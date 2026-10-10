"""Fresh feasibility-recovery grant using the existing research lifecycle."""
import os
os.environ['NMPC_FEASIBILITY_RECOVERY']='1'
if __name__=='__main__':
    from tools.research_casadi_feedback import main
    main()
