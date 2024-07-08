import ezdxf
from ezdxf.audit import Auditor

doc = ezdxf.readfile("assets/gift.dxf")
auditor = Auditor(doc)
errors = list(auditor.run())
for error in errors:
    print(error)