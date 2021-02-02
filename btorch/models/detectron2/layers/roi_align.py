import detectron2.layers.roi_align as ra
from .....btorch.module import TorchModule


class ROIAlignRotated(TorchModule):
    def __init__(self, *args, name=None, **kwargs):
        super(ROIAlignRotated, self).__init__(module=ra.ROIAlign(*args, **kwargs),
                                              In=('x', 'rois'), Out=1, name=name)
        self.lock_ports = True
