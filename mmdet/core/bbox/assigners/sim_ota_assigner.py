import warnings

import torch
import torch.nn.functional as F

from mmdet.core import bbox_overlaps
from ..builder import BBOX_ASSIGNERS
from .base_assigner import BaseAssigner


@BBOX_ASSIGNERS.register_module()
class SimOTAAssigner(BaseAssigner):
    """Computes matching between predictions and ground truth.

    Args:
        center_radius (int | float, optional): Ground truth center size
            to judge whether a prior is in center. Default 2.5.
        candidate_topk (int, optional): The candidate top-k which used to
            get top-k ious to calculate dynamic-k. Default 10.
    """

    def __init__(self, center_radius=2.5, candidate_topk=10):
        self.center_radius = center_radius
        self.candidate_topk = candidate_topk

    def assign(self,
               pred_scores,
               priors,
               decoded_bboxes,
               gt_bboxes,
               gt_labels,
               gt_bboxes_ignore=None,
               eps=1e-7):
        """Assign gt to priors using SimOTA. It will switch to CPU mode when
        GPU is out of memory.

        Args:
            pred_scores (Tensor): Classification scores of one image,
                a 2D-Tensor with shape [num_priors, num_classes]
            priors (Tensor): All priors of one image, a 2D-Tensor with shape
                [num_priors, 4] in [cx, xy, stride_w, stride_y] format.
            gt_bboxes (Tensor): Ground truth bboxes of one image, a 2D-Tensor
                with shape [num_gts, 4] in [tl_x, tl_y, br_x, br_y] format.
            gt_labels (Tensor): Ground truth labels of one image, a Tensor
                with shape [num_gts].
            gt_bboxes_ignore (Tensor, optional): Ground truth bboxes that are
                labelled as `ignored`, e.g., crowd boxes in COCO.
            eps (float): A value added to the denominator for numerical
            stability. Default 1e-7.

        Returns:
        """
        try:
            assign_results = self._assign(pred_scores, priors, decoded_bboxes,
                                          gt_bboxes, gt_labels,
                                          gt_bboxes_ignore, eps)
            return assign_results
        except RuntimeError:
            origin_device = pred_scores.device
            warnings.warn('OOM RuntimeError is raised due to the huge memory '
                          'cost during label assignment. CPU mode is applied '
                          'in this batch. If you want to avoid this issue, '
                          'try to reduce the batch size or image size.')
            torch.cuda.empty_cache()

            pred_scores = pred_scores.cpu()
            priors = priors.cpu()
            decoded_bboxes = decoded_bboxes.cpu()
            gt_bboxes = gt_bboxes.cpu().float()
            gt_labels = gt_labels.cpu()

            assign_results = self._assign(pred_scores, priors, decoded_bboxes,
                                          gt_bboxes, gt_labels,
                                          gt_bboxes_ignore, eps)
            (gt_matched_classes, valid_mask, pred_ious_this_matching,
             matched_gt_inds, num_fg) = assign_results

            return (gt_matched_classes.to(origin_device),
                    valid_mask.to(origin_device),
                    pred_ious_this_matching.to(origin_device),
                    matched_gt_inds.to(origin_device), num_fg)

    def _assign(self,
                pred_scores,
                priors,
                decoded_bboxes,
                gt_bboxes,
                gt_labels,
                gt_bboxes_ignore=None,
                eps=1e-7):
        """Assign gt to priors using SimOTA.

        Args:
            pred_scores (Tensor): Classification scores of one image,
                a 2D-Tensor with shape [num_priors, num_classes]
            priors (Tensor): All priors of one image, a 2D-Tensor with shape
                [num_priors, 4] in [cx, xy, stride_w, stride_y] format.
            gt_bboxes (Tensor): Ground truth bboxes of one image, a 2D-Tensor
                with shape [num_gts, 4] in [tl_x, tl_y, br_x, br_y] format.
            gt_labels (Tensor): Ground truth labels of one image, a Tensor
                with shape [num_gts].
            gt_bboxes_ignore (Tensor, optional): Ground truth bboxes that are
                labelled as `ignored`, e.g., crowd boxes in COCO.
            eps (float): A value added to the denominator for numerical
            stability. Default 1e-7.

        Returns:
        """
        INF = 100000000
        num_gt = gt_bboxes.size(0)

        valid_mask, is_in_boxes_and_center = self.get_in_gt_and_in_center_info(
            priors, gt_bboxes)

        valid_decoded_bbox = decoded_bboxes[valid_mask]
        valid_pred_scores = pred_scores[valid_mask]
        num_valid = valid_decoded_bbox.size(0)

        # TODO: use match cost
        pair_wise_ious = bbox_overlaps(valid_decoded_bbox, gt_bboxes)
        iou_cost = -torch.log(pair_wise_ious + eps)  # [num_valid, num_gt]

        gt_onehot_label = (
            F.one_hot(gt_labels.to(torch.int64),
                      pred_scores.shape[-1]).float().unsqueeze(0).repeat(
                          num_valid, 1, 1))

        valid_pred_scores = valid_pred_scores.unsqueeze(1).repeat(1, num_gt, 1)
        cls_cost = F.binary_cross_entropy(
            valid_pred_scores.sqrt_(), gt_onehot_label,
            reduction='none').sum(-1)  # [num_valid, num_gt]

        cost_matrix = cls_cost + 3.0 * iou_cost + INF * (
            ~is_in_boxes_and_center)

        (num_fg, gt_matched_classes,
         pred_ious_this_matching, matched_gt_inds) = \
            self.dynamic_k_matching(
                cost_matrix, pair_wise_ious, gt_labels, num_gt, valid_mask)
        # TODO: use AssignResult
        return (gt_matched_classes, valid_mask, pred_ious_this_matching,
                matched_gt_inds, num_fg)

    def get_in_gt_and_in_center_info(self, priors, gt_bboxes):
        num_gt = gt_bboxes.size(0)

        repeated_x = priors[:, 0].unsqueeze(1).repeat(1, num_gt)
        repeated_y = priors[:, 1].unsqueeze(1).repeat(1, num_gt)
        repeated_stride_x = priors[:, 2].unsqueeze(1).repeat(1, num_gt)
        repeated_stride_y = priors[:, 3].unsqueeze(1).repeat(1, num_gt)

        # is prior centers in gt bboxes, shape: [n_prior, n_gt]
        l_ = repeated_x - gt_bboxes[:, 0]
        t_ = repeated_y - gt_bboxes[:, 1]
        r_ = gt_bboxes[:, 2] - repeated_x
        b_ = gt_bboxes[:, 3] - repeated_y

        deltas = torch.stack([l_, t_, r_, b_], dim=1)
        is_in_gts = deltas.min(dim=1).values > 0
        is_in_gts_all = is_in_gts.sum(dim=1) > 0

        # is prior centers in gt centers
        gt_cxs = (gt_bboxes[:, 0] + gt_bboxes[:, 2]) / 2.0
        gt_cys = (gt_bboxes[:, 1] + gt_bboxes[:, 3]) / 2.0
        ct_box_l = gt_cxs - self.center_radius * repeated_stride_x
        ct_box_t = gt_cys - self.center_radius * repeated_stride_y
        ct_box_r = gt_cxs + self.center_radius * repeated_stride_x
        ct_box_b = gt_cys + self.center_radius * repeated_stride_y

        cl_ = repeated_x - ct_box_l
        ct_ = repeated_y - ct_box_t
        cr_ = ct_box_r - repeated_x
        cb_ = ct_box_b - repeated_y

        ct_deltas = torch.stack([cl_, ct_, cr_, cb_], dim=1)
        is_in_cts = ct_deltas.min(dim=1).values > 0
        is_in_cts_all = is_in_cts.sum(dim=1) > 0

        # in boxes or in centers, shape: [num_priors]
        is_in_gts_or_centers = is_in_gts_all | is_in_cts_all

        # both in boxes and centers, shape: [num_fg, num_gt]
        is_in_boxes_and_centers = (
            is_in_gts[is_in_gts_or_centers, :]
            & is_in_cts[is_in_gts_or_centers, :])
        return is_in_gts_or_centers, is_in_boxes_and_centers

    def dynamic_k_matching(self, cost, pair_wise_ious, gt_classes, num_gt,
                           fg_mask):
        matching_matrix = torch.zeros_like(cost)
        # select candidate topk ious for dynamic-k calculation
        topk_ious, _ = torch.topk(pair_wise_ious, self.candidate_topk, dim=0)
        # calculate dynamic k for each gt
        dynamic_ks = torch.clamp(topk_ious.sum(0).int(), min=1)
        for gt_idx in range(num_gt):
            _, pos_idx = torch.topk(
                cost[:, gt_idx], k=dynamic_ks[gt_idx].item(), largest=False)
            matching_matrix[:, gt_idx][pos_idx] = 1.0

        del topk_ious, dynamic_ks, pos_idx

        prior_match_gt_mask = matching_matrix.sum(1) > 1
        if prior_match_gt_mask.sum() > 0:
            cost_min, cost_argmin = torch.min(
                cost[prior_match_gt_mask, :], dim=1)
            matching_matrix[prior_match_gt_mask, :] *= 0.0
            matching_matrix[prior_match_gt_mask, cost_argmin] = 1.0
        fg_mask_inboxes = matching_matrix.sum(1) > 0.0
        num_fg = fg_mask_inboxes.sum().item()

        fg_mask[fg_mask.clone()] = fg_mask_inboxes

        matched_gt_inds = matching_matrix[fg_mask_inboxes, :].argmax(1)
        gt_matched_classes = gt_classes[matched_gt_inds]

        pred_ious_this_matching = (matching_matrix *
                                   pair_wise_ious).sum(1)[fg_mask_inboxes]
        return (num_fg, gt_matched_classes, pred_ious_this_matching,
                matched_gt_inds)
