from mmcv.runner.hooks.lr_updater import CosineAnnealingLrUpdaterHook, annealing_cos
from mmcv.runner.hooks import HOOKS
from mmcv.runner import get_dist_info


@HOOKS.register_module()
class CosineAnnealingWithStopLrUpdaterHook(CosineAnnealingLrUpdaterHook):
    """Cosine Annealing with stop LR Scheduler used in YOLOX.
    The difference from the `CosineAnnealingLrUpdaterHook` is that
    when the current running epoch is greater than `max_epochs-no_aug_epoch`,
    a fixed learning rate will be used.

    Args:
        no_aug_epoch (int): The epoch of close data augmentation.
        warmup_ratio (float): LR used at the beginning of warmup.
    """

    def __init__(self, no_aug_epoch,  warmup_ratio, **kwargs):
        _, work_size = get_dist_info()
        self.base_lr_ = warmup_ratio * work_size
        self.no_aug_epoch = no_aug_epoch
        super(CosineAnnealingWithStopLrUpdaterHook, self).__init__(warmup_ratio=self.base_lr_, **kwargs)

    def get_warmup_lr(self, cur_iters):
        def _get_warmup_lr(cur_iters, regular_lr):
            k = self.warmup_ratio * pow(
                cur_iters / float(self.warmup_iters), 2
            )
            warmup_lr = [k for _lr in regular_lr]
            return warmup_lr

        if isinstance(self.regular_lr, dict):
            lr_groups = {}
            for key, regular_lr in self.regular_lr.items():
                lr_groups[key] = _get_warmup_lr(cur_iters, regular_lr)
            return lr_groups
        else:
            return _get_warmup_lr(cur_iters, self.regular_lr)

    def get_lr(self, runner, base_lr):

        no_aug_iter = len(runner.data_loader) * self.no_aug_epoch

        if self.by_epoch:
            progress = runner.epoch
            max_progress = runner.max_epochs
        else:
            progress = runner.iter
            max_progress = runner.max_iters

        if self.min_lr_ratio is not None:
            target_lr = self.base_lr_ * self.min_lr_ratio
        else:
            target_lr = self.min_lr

        if progress >= max_progress - no_aug_iter:
            return target_lr
        else:
            return annealing_cos(self.base_lr_, target_lr,
                                 (progress - self.warmup_iters) / (max_progress - self.warmup_iters - no_aug_iter))
