function model = sr_model(spec)
% Original adapter, based on frozen sv_model.m at e1ae7633 (not imported).
% Upstream custom basis and section matrices preserve physical axes exactly.
started=tic;
if isstruct(spec.links), spec.links=num2cell(spec.links); end
S=SorosimLinkage('empty'); S.Z_order=[];
S.VLinks=SorosimLink.empty(1,0); S.N=numel(spec.links);
S.ndof=numel(spec.coordinate_order); S.CVRods=cell(S.N,1);
S.iLpre=zeros(S.N,1); S.LinkIndex=(1:S.N)'; S.g_ini=zeros(4*S.N,4);
model.node_indices=cell(S.N,1); model.nodes=cell(S.N,1);
signal=1; natural=zeros(S.ndof,1);
for k=1:S.N
    c=spec.links{k};
    L=SorosimLink('empty'); L.jointtype='N'; L.Kj=[]; L.Dj=[];
    S.iLpre(k)=c.parent; S.g_ini((k-1)*4+(1:4),:)=c.connection;
    if strcmp(c.kind,'flexible_segment')
        L.linktype='s'; L.npie=2; L.L=c.length; L.ld={c.length};
        L.gi={eye(4)}; L.gf={eye(4)};
        joint=SorosimRod(L,zeros(6,0));
        rod=SorosimRod(); rod.dof=[]; rod.Link=L; rod.div=1;
        rod.Type='Custom Basis';
        rod.Phi_h=@(s) custom_basis(s,c.knots,c.basis_strategy);
        rod.xi_starfn=@(~) [0;0;0;1;0;0];
        rod.nip=numel(c.nodes); rod.Xs=c.nodes(:); rod.Ws=c.weights(:);
        rod.dof=2*numel(c.knots); rod.UpdatePhis(); rod.UpdateXi_star();
        rod.Ms=stack_matrices(c.mass); rod.Es=stack_matrices(c.elastic); rod.Gs=stack_matrices(c.viscous);
        S.CVRods{k}=[joint,rod];
        model.nodes{k}=rod.Xs;
        model.node_indices{k}=signal+1+(0:rod.nip-1);
        ix=c.start+(1:rod.dof);
        for j=1:rod.nip
            rows=(j-1)*6+(1:6); P=rod.Phi(rows,:);
            natural(ix)=natural(ix)+rod.Ws(j)*P'*rod.Es(rows,:)*c.natural(j,:)';
        end
        signal=signal+1+rod.nip;
    else
        L.linktype='r'; L.npie=1; L.L=0;
        L.gi=eye(4); L.gi(1:3,4)=c.com(:);
        L.gf=inv(L.gi); % next link connection is relative to component origin
        L.M=blkdiag(c.inertia,c.mass_kg*eye(3));
        S.CVRods{k}=SorosimRod(L,zeros(6,0));
        model.nodes{k}=0; model.node_indices{k}=signal+1;
        signal=signal+2;
    end
    S.VLinks(k)=L;
end
[S.nsig,S.nj]=find_nsig_nj(S);
assert(signal-1==S.nsig,'SOROSIM_SIGNAL_INDEX_MISMATCH');
S.Z_order=4; S.Gravity=true; S.G=[0;0;0;spec.gravity(:)];
S.CEF=false; S.CA=false; S.CAI=false; S.Actuated=false;
S.CLprecompute=struct('nCLp',0); S.K=S.findK(); S.D=S.findD(); S.Damped=true;
model.S=S; model.T=diag(spec.coordinate_scale); model.natural=natural;
model.spec=spec;
model.description=struct('model_identity',spec.identity,'coordinates',S.ndof, ...
    'links',S.N,'signals',S.nsig,'coordinate_transform',model.T, ...
    'coordinate_rank',rank(model.T),'construction_s',toc(started), ...
    'native_actuation',false,'integration','Zanna order 4, Gauss on each structural interval');
end

function P=custom_basis(s,knots,strategy)
knots=knots(:)';
if strcmp(strategy,'first_order')
    v=[1,2*s-1];
else
    j=find(knots<=s,1,'last'); j=min(j,numel(knots)-1);
    a=(s-knots(j))/(knots(j+1)-knots(j));
    v=zeros(1,numel(knots)); v(j)=1-a;v(j+1)=a;
end
P=zeros(6,2*numel(v)); P(2,1:numel(v))=v; P(3,numel(v)+(1:numel(v)))=v;
end

function result=stack_matrices(values)
% jsondecode produces [nodes,6,6], so extract without column-order guessing.
result=zeros(6*size(values,1),6);
for j=1:size(values,1), result((j-1)*6+(1:6),:)=squeeze(values(j,:,:)); end
end
