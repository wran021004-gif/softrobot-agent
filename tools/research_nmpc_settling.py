"""A fresh bounded grant, using the established sequential research lifecycle."""
import os
os.environ['NMPC_SETTLING_FOLLOWUP']='1'
if __name__=='__main__':
    from tools.research_casadi_feedback import main
    main()
