"""Experimental exact scalar evaluation of one GVS force-balance kernel.

No physical, objective, constraint or solver-policy changes. Expansion is local
to a single dynamics evaluation; the complete horizon is not expanded here.
"""
import time
import hashlib
import subprocess
from pathlib import Path
import casadi as ca
import numpy as np

VERSION='gvs_scalar_force_kernel@1.0.0'


def mass_form_kernel(functions):
    """Equivalent existing M(q)*a-force(q,v,u), avoiding nested wrench AD."""
    start=time.perf_counter();n=functions.q_symbol.numel();m=functions.u_symbol.numel()
    x=ca.MX.sym('x',2*n);u=ca.MX.sym('u',m);a=ca.MX.sym('a',n)
    mass,force=functions.implicit_terms(x,u)
    f=ca.Function('gvs_mass_form_force_balance',[x,u,a],[mass@a-force],{'cse':True,'der_options':{'cse':True}})
    z=ca.MX.sym('arguments',3*n+m);r=f(z[:2*n],z[2*n:2*n+m],z[2*n+m:])
    j=ca.Function('gvs_mass_form_jacobian',[z],[r,ca.jacobian(r,z)],{'ad_weight':1.})
    return dict(function=f,jacobian=j,construction_s=time.perf_counter()-start,version='gvs_mass_form_kernel@1.0.0')


def scalar_kernel(functions):
    started=time.perf_counter()
    function=functions.implicit_residual.expand('gvs_scalar_force_balance')
    n=functions.q_symbol.numel();m=functions.u_symbol.numel()
    z=ca.MX.sym('force_arguments',3*n+m)
    residual=function(z[:2*n],z[2*n:2*n+m],z[2*n+m:])
    jacobian=ca.Function('gvs_scalar_force_jacobian',[z],[residual,ca.jacobian(residual,z)],{'ad_weight':1.})
    return dict(function=function,jacobian=jacobian,construction_s=time.perf_counter()-started,
        scalar_nodes=function.n_nodes(),version=VERSION)


def evaluate_pair(functions,kernel,state,input_n,acceleration):
    n=functions.q_symbol.numel();m=functions.u_symbol.numel();z=ca.MX.sym('original_arguments',3*n+m)
    residual=functions.implicit_residual(z[:2*n],z[2*n:2*n+m],z[2*n+m:])
    original=ca.Function('gvs_original_force_jacobian',[z],[residual,ca.jacobian(residual,z)],{'ad_weight':1.})
    values=np.r_[state,input_n,acceleration];results=[]
    for name,f in (('original',original),('scalar',kernel['jacobian'])):
        start=time.perf_counter();r,j=f(values);elapsed=time.perf_counter()-start
        results.append(dict(method=name,residual=np.asarray(r).ravel().tolist(),jacobian=np.asarray(j).tolist(),evaluation_s=elapsed))
    a,b=results
    dr=float(np.max(abs(np.asarray(a['residual'])-b['residual'])));dj=float(np.max(abs(np.asarray(a['jacobian'])-b['jacobian'])))
    scale=max(float(np.max(abs(np.asarray(a['jacobian'])))),1.)
    return dict(evaluations=results,residual_difference=dr,jacobian_difference=dj,jacobian_relative_difference=dj/scale,
        equivalent=dr<=1e-10 and dj/scale<=1e-8,speedup=a['evaluation_s']/max(b['evaluation_s'],1e-12))


NATIVE_VERSION='gvs_native_force_kernel@1.0.0'


def run_compiler(command,log,timeout_s):
    start=time.perf_counter();compiler=command[0];log=Path(log)
    with log.open('w',encoding='utf8') as out:
        process=subprocess.Popen(command,stdout=out,stderr=out,creationflags=subprocess.CREATE_NO_WINDOW)
        try:code=process.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            process.kill();process.wait()
            # Builds using this task-private portable compiler are serialized.
            # WMI/taskkill tree enumeration is denied in the managed sandbox.
            # Match the exact task-local executable, never a system compiler.
            target=str(Path(compiler).with_name('clang-23.exe').resolve()).replace("'","''")
            cleanup="Get-Process -Name clang-23 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq '"+target+"' } | Stop-Process -ErrorAction SilentlyContinue"
            subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',cleanup],capture_output=True,timeout=15.,creationflags=subprocess.CREATE_NO_WINDOW)
            raise
    if code:raise RuntimeError('NATIVE_COMPILATION_FAILED: '+log.read_text(encoding='utf8')[-1500:])
    return time.perf_counter()-start


def compile_existing(folder,compiler,*,optimization='-O0',timeout_s=180.,extra_flags=(),source_name='force_native'):
    """Bounded native retry reuses the exact generated source, never old timings."""
    folder=Path(folder);source=folder/(source_name+'.c');suffix=optimization.lstrip('-').lower();library=folder/f'{source_name}_{suffix}.dll'
    command=[str(compiler),optimization,*extra_flags,'-fno-fast-math','-shared',str(source),'-o',str(library)]
    compile_s=run_compiler(command,folder/f'compiler_{suffix}_output.txt',timeout_s)
    f=ca.external('gvs_force_balance',str(library))
    return dict(function=f,jacobian=f.jacobian(),version='gvs_native_force_kernel@1.1.0',
        compile_s=compile_s,generation_s=0.,source_reused=True,library=str(library),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
        compiler_command=command)


def build_native(functions,folder,compiler):
    """Compile exact MX force balance and its exact Jacobian; no fast-math."""
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);start=time.perf_counter()
    f=functions.implicit_residual;j=f.jacobian()
    generator=ca.CodeGenerator('force_native.c',{'with_header':True})
    generator.add(f);generator.add(j);generator.generate(folder.as_posix()+'/')
    generation_s=time.perf_counter()-start;source=folder/'force_native.c';library=folder/'force_native.dll'
    command=[str(compiler),'-O2','-fno-fast-math','-shared',str(source),'-o',str(library)]
    compile_s=run_compiler(command,folder/'compiler_output.txt',600.)
    compiled=ca.external(f.name(),str(library));jacobian=compiled.jacobian()
    return dict(function=compiled,jacobian=jacobian,version=NATIVE_VERSION,source_bytes=source.stat().st_size,
        generation_s=generation_s,compile_s=compile_s,library=str(library),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
        function_identity=hashlib.sha256(f.serialize().encode()).hexdigest(),compiler_command=command)


def evaluate_native(kernel,state,input_n,acceleration):
    started=time.perf_counter();f=kernel['function'];j=kernel['jacobian']
    r=f(state,input_n,acceleration);blocks=j(state,input_n,acceleration,r)
    elapsed=time.perf_counter()-started
    return dict(residual=np.asarray(r).ravel().tolist(),jacobian=np.hstack([np.asarray(b) for b in blocks]).tolist(),evaluation_s=elapsed)


def build_native_reverse(functions,folder,compiler):
    """Generate scalar reverse AD, avoiding the very large full-Jacobian C unit."""
    folder=Path(folder);folder.mkdir(exist_ok=True);started=time.perf_counter()
    f=functions.implicit_residual;reverse=f.reverse(1)
    generator=ca.CodeGenerator('force_reverse.c',{'with_header':True});generator.add(f);generator.add(reverse)
    generator.generate(folder.as_posix()+'/');generation_s=time.perf_counter()-started
    source=folder/'force_reverse.c';library=folder/'force_reverse.dll'
    # Run the actual driver with integrated cc1. The portable clang.exe is a
    # launcher; killing that launcher alone did not terminate its compilation.
    driver=Path(compiler).with_name('clang-23.exe')
    command=[str(driver),'-fintegrated-cc1','-O1','-fno-inline','-fno-fast-math','-shared',str(source),'-o',str(library)]
    print('Reverse AD source bytes: '+str(source.stat().st_size),flush=True)
    compile_s=run_compiler(command,folder/'compiler_output.txt',180.)
    compiled=ca.external(f.name(),str(library))
    return dict(function=compiled,jacobian=compiled.jacobian(),version='gvs_native_reverse_kernel@1.0.0',
        source_bytes=source.stat().st_size,generation_s=generation_s,compile_s=compile_s,library=str(library),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
        function_identity=hashlib.sha256(f.serialize().encode()).hexdigest(),compiler_command=command)


def build_native_mixed(folder,compiler):
    """Optimize small cell/derivative kernels, leaving giant orchestration alone.

    The generated reverse unit has 4.8/11.0 MB force/adjoint functions. This
    annotation-only variant avoids their compiler optimization passes while
    optimizing the shared 25-100 KB cell pose derivative functions.
    """
    folder=Path(folder);original=folder/'force_reverse.c';source=original.read_text(encoding='utf8')
    changed=[]
    for name in ('casadi_f0','casadi_f7'):
        needle='static int '+name+'('
        count=source.count(needle)
        if count!=1:raise ValueError('MIXED_COMPILATION_SOURCE_LAYOUT_CHANGED')
        source=source.replace(needle,'static __attribute__((optnone)) int '+name+'(')
        changed.append(dict(function=name,annotation='optnone',occurrences=count))
    (folder/'force_mixed.c').write_text(source,encoding='utf8')
    result=compile_existing(folder,compiler,source_name='force_mixed',optimization='-O2',extra_flags=('-fno-inline',),timeout_s=120.)
    result.update(version='gvs_native_mixed_kernel@1.0.0',annotation_changes=changed,
        original_source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
        rationale='Exact same arithmetic graph; compiler optimization disabled only for two giant orchestration functions.',
        compiler_attribute_reference='https://clang.llvm.org/docs/AttributeReference.html#optnone')
    return result


def build_native_split(folder,compiler,*,shared_runtime=False):
    """Separate O0 orchestration from O2 helper translation units, exact graph."""
    import re
    folder=Path(folder);original=folder/'force_reverse.c';source=original.read_text(encoding='utf8')
    starts=list(re.finditer(r'static int (casadi_f\d+)\([^;]+?\) \{',source));functions=[]
    for match in starts:
        opening=match.end()-1;depth=1;end=opening+1
        while depth:
            depth+=(source[end]=='{')-(source[end]=='}');end+=1
        functions.append(dict(name=match.group(1),start=match.start(),end=end,
            prototype=source[match.start():opening].removeprefix('static ').strip()+';',
            body=source[match.start():end].removeprefix('static ')))
    big=[f for f in functions if f['name'] in ('casadi_f0','casadi_f7')]
    if len(big)!=2:raise ValueError('SPLIT_SOURCE_LAYOUT_CHANGED')
    prefix=source[:starts[0].start()]
    if shared_runtime:
        runtime=list(re.finditer(r'(?m)^(?:void|casadi_real|casadi_int|int) casadi_\w+\([^;]+?\) \{',prefix))
        giant_prefix=prefix
        for match in reversed(runtime):
            opening=match.end()-1;depth=1;end=opening+1
            while depth:depth+=(prefix[end]=='{')-(prefix[end]=='}');end+=1
            giant_prefix=giant_prefix[:match.start()]+prefix[match.start():opening].strip()+';'+giant_prefix[end:]
        if len(runtime)!=9:raise ValueError('SHARED_RUNTIME_LAYOUT_CHANGED')
    else:
        # The first split experiment used local runtime helpers in each unit.
        prefix=re.sub(r'(?m)^(void|casadi_real|casadi_int|int)( casadi_\w+\()',r'static \1\2',prefix)
        giant_prefix=prefix
    prototypes='\n'.join(f['prototype'] for f in functions)+'\n'
    tail=source[starts[0].start():]
    for f in reversed(big):
        lo=f['start']-starts[0].start();hi=f['end']-starts[0].start();tail=tail[:lo]+tail[hi:]
    tail=tail.replace('static int casadi_f','int casadi_f')
    units={'orchestration':giant_prefix+prototypes+'\n'.join(f['body'] for f in big),
        'helpers':prefix+prototypes+tail};commands=[];times=[];hashes={}
    suffix='_shared' if shared_runtime else ''
    for name,body in units.items():
        path=folder/(name+suffix+'.c');path.write_text(body,encoding='utf8');hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        command=[str(compiler),'-O0' if name=='orchestration' else '-O2','-fno-inline','-fno-fast-math','-c',str(path),'-o',str(folder/(name+suffix+'.o'))]
        commands.append(command);times.append(run_compiler(command,folder/(name+suffix+'_compiler.txt'),120.))
        print('Compiled '+name+' in '+str(times[-1])+' s',flush=True)
    library=folder/('force_split'+suffix+'.dll');command=[str(compiler),'-shared',str(folder/('orchestration'+suffix+'.o')),str(folder/('helpers'+suffix+'.o')),'-o',str(library)]
    commands.append(command);times.append(run_compiler(command,folder/('split_link'+suffix+'.txt'),30.))
    f=ca.external('gvs_force_balance',str(library))
    return dict(function=f,jacobian=f.jacobian(),version='gvs_native_split_kernel@2.0.0' if shared_runtime else 'gvs_native_split_kernel@1.0.0',library=str(library),
        source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),translation_unit_hashes=hashes,
        library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),compiler_commands=commands,compile_stage_s=times,
        compile_s=sum(times),source_reused=True,arithmetic_changes=False,shared_optimized_runtime=shared_runtime,
        change='Only function linkage and translation-unit partition: O0 giant functions, O2 shared small helper functions. No CSE/arithmetic/model rewrite.')


def build_native_chunked(folder,compiler,*,full_jacobian=False):
    """Split generated MX operation blocks, preserving cross-block temporaries.

    Scoped to the frozen CasADi 3.7.2 force/adjoint source layout. Unknown
    declarations fail closed. No expression, derivative or arithmetic changes.
    """
    import re
    folder=Path(folder);original=folder/('force_native.c' if full_jacobian else 'force_reverse.c');source=original.read_text(encoding='utf8');changes=[]
    for name in ('casadi_f7','casadi_f0'):
        match=re.search(r'static int '+name+r'\([^;]+?\) \{',source)
        opening=match.end()-1;depth=1;end=opening+1
        while depth:depth+=(source[end]=='{')-(source[end]=='}');end+=1
        first=source.index('/* #0:',opening,end);declarations=source[opening+1:first]
        aliases={};scalars=[];readonly=[];aux=[]
        for declaration in declarations.split(';'):
            declaration=declaration.strip()
            if not declaration:continue
            parsed=re.fullmatch(r'(const casadi_real|const casadi_int|casadi_real|casadi_int)\s+(.+)',declaration,re.S)
            if parsed is None:raise ValueError('CHUNKED_UNKNOWN_DECLARATION')
            kind,variables=parsed.groups();kept=[]
            for variable in variables.split(','):
                variable=variable.strip();pointer=re.fullmatch(r'\*(w\d+)=w\+(\d+)',variable)
                if pointer:aliases[pointer[1]]='(w+'+pointer[2]+')'
                elif re.fullmatch(r'w\d+',variable):
                    aliases[variable]='frame->scalars['+str(len(scalars))+']';scalars.append(variable)
                elif re.fullmatch(r'\*wr\d+',variable):
                    key=variable[1:];aliases[key]='frame->readonly['+str(len(readonly))+']';readonly.append(key)
                else:kept.append(variable)
            if kept:aux.append(kind+' '+','.join(kept)+';')
        auxiliary='\n'.join(aux)
        if re.search(r'\bw[r]?\d+\b',auxiliary):raise ValueError('CHUNKED_UNCLASSIFIED_WORK_VARIABLE')
        body=source[first:end-1];body=re.sub(r'\b(?:w\d+|wr\d+)\b',lambda m:aliases[m[0]],body)
        body=re.sub(r'\breturn 0;\s*$', '',body)
        starts=[m.start() for m in re.finditer(r'/\* #\d+:',body)];starts.append(len(body))
        chunks=[''.join(body[starts[i]:starts[min(i+250,len(starts)-1)]]) for i in range(0,len(starts)-1,250)]
        frame_type=name+'_frame';frame_definition='typedef struct { casadi_real scalars['+str(max(1,len(scalars)))+']; const casadi_real* readonly['+str(max(1,len(readonly)))+']; } '+frame_type+';\n'
        signature='const casadi_real** arg, casadi_real** res, casadi_int* iw, casadi_real* w, int mem'
        helpers=[];calls=[]
        for i,chunk in enumerate(chunks):
            helper=name+'_chunk_'+str(i)
            helpers.append('static int '+helper+'('+signature+', '+frame_type+'* frame) {\n'+auxiliary+'\n'+chunk+'\nreturn 0;\n}\n')
            calls.append('if ('+helper+'(arg,res,iw,w,mem,frame)) {free(frame);return 1;}')
        wrapper='static int '+name+'('+signature+') {\n'+frame_type+'* frame=('+frame_type+'*)malloc(sizeof('+frame_type+'));\nif (!frame) return 1;\n'+'\n'.join(calls)+'\nfree(frame);return 0;\n}\n'
        source=source[:match.start()]+frame_definition+''.join(helpers)+wrapper+source[end:]
        changes.append(dict(function=name,chunk_count=len(chunks),maximum_mx_operations_per_chunk=250,scalar_slots=len(scalars),readonly_pointer_slots=len(readonly),auxiliary_declarations=auxiliary))
    source='#include <stdlib.h>\n'+source;(folder/'force_chunked.c').write_text(source,encoding='utf8')
    result=compile_existing(folder,compiler,source_name='force_chunked',optimization='-O1',extra_flags=('-fno-inline',),timeout_s=900. if full_jacobian else 240.)
    result.update(version='gvs_native_chunked_kernel@2.0.0' if full_jacobian else 'gvs_native_chunked_kernel@1.0.1',chunking=changes,full_jacobian=full_jacobian,
        original_source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
        change='Complete MX operation blocks partitioned into <=250-operation functions; pointer aliases retain workspace offsets, scalar and read-only pointer temporaries explicitly persist in an allocated frame. Arithmetic and ordering unchanged.')
    return result
