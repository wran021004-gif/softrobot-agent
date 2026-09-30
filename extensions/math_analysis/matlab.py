"""One Engine lifecycle per public batch, using the existing integration."""
import importlib.metadata
import numpy as np
from tools.matlab_tools import MatlabTools


class MatlabBatch:
    def __enter__(self):
        self.tools=MatlabTools()
        try:
            e=self.tools.eng
            self.environment=dict(release=str(e.version('-release',nargout=1)),version=self.tools.version(),
                engine=importlib.metadata.version('matlabengine'),control_toolbox=e.ver('control',nargout=1),
                control_license=bool(e.license('test','Control_Toolbox',nargout=1)))
            if not self.environment['control_toolbox'] or not self.environment['control_license']:
                raise RuntimeError('CONTROL_SYSTEM_TOOLBOX_UNAVAILABLE')
            return self
        except BaseException:
            self.tools.close(); raise

    def __exit__(self,*exc): self.tools.close()

    def calculate(self,A,B,C,D,drift,p):
        import matlab
        values=[matlab.double(np.asarray(v).tolist()) for v in (A,B,C,D,drift.reshape(-1,1))]
        out=self.tools.eng.analyze_linear_model(*values,float(p.period_s),matlab.double([p.windows_s]),
            matlab.double([p.frequency_rad_s]),float(p.pole_margin_s_inv),nargout=1)
        real=np.asarray(out['frequency_real']); imag=np.asarray(out['frequency_imag'])
        return dict(A_d=np.asarray(out['A_d']).tolist(),B_d=np.asarray(out['B_d']).tolist(),
            drift_d=np.asarray(out['drift_d']).reshape(-1).tolist(),poles=np.asarray(out['poles']).tolist(),
            frequency_response=[dict(real=real[:,:,i].tolist(),imag=imag[:,:,i].tolist()) for i in range(len(p.frequency_rad_s))],
            singular_values=np.asarray(out['singular_values']).tolist(),
            continuous_gramians=[np.asarray(w).tolist() for w in out['continuous_gramians']],
            held_gramians=[np.asarray(w).tolist() for w in out['held_gramians']],
            gramian_algorithms=list(out['gramian_algorithms']))
