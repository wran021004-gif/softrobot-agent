"""Fresh initialization study using the existing provider/Host lifecycle."""
import os

os.environ['NMPC_INITIALIZATION_DIAGNOSIS']='1'

if __name__=='__main__':
    from tools.research_casadi_feedback import main
    main()
