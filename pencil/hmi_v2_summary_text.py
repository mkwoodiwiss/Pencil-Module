"""Final summary-text corrections for the MEU v2 process tabs."""

from __future__ import annotations

from .hmi_v2_post_scrub_dialog import HMI as _PostScrubDialogHMI


class HMI(_PostScrubDialogHMI):
    """Keep Flush and Post-Scrub summaries consistent with Test."""

    def _update_flush_summary(self) -> None:
        left = (
            f"Filter: {self.flush_filt_target_weight_var.get():g} g\n"
            f"Backwash: {self.flush_bw_target_weight_var.get():g} g"
        )
        right = (
            f"Purge: {self.flush_purge_time_var.get():g} s\n"
            f"Cycles: {self.flush_cycle_count_var.get()}"
        )
        if hasattr(self, "flush_summary_left_var"):
            self.flush_summary_left_var.set(left)
            self.flush_summary_right_var.set(right)
        if hasattr(self, "flush_summary_var"):
            self.flush_summary_var.set(f"{left}\n{right}")

    def _update_post_scrub_summary(self) -> None:
        filter_by_weight = self.post_scrub_filt_use_weight_var.get()
        backwash_by_weight = self.post_scrub_bw_use_weight_var.get()
        filter_value = (
            self.post_scrub_filt_target_weight_var.get()
            if filter_by_weight
            else self.post_scrub_filt_target_time_var.get()
        )
        backwash_value = (
            self.post_scrub_bw_target_weight_var.get()
            if backwash_by_weight
            else self.post_scrub_bw_target_time_var.get()
        )
        left = (
            f"Filter: {filter_value:g} {'g' if filter_by_weight else 's'}\n"
            f"Backwash: {backwash_value:g} {'g' if backwash_by_weight else 's'}\n"
            f"Purge: {self.post_scrub_purge_time_var.get():g} s\n"
            f"Cycles: {self.post_scrub_cycle_count_var.get()}\n"
            f"Sample: {self.post_scrub_sample_time_var.get():g} s"
        )
        right = (
            f"Project: {self.post_scrub_project_var.get() or '--'}\n"
            f"Module: {self.post_scrub_module_id_var.get() or '--'}\n"
            f"Sample ID: {self.post_scrub_sample_id_var.get() or '--'}"
        )
        if hasattr(self, "post_scrub_summary_left_var"):
            self.post_scrub_summary_left_var.set(left)
            self.post_scrub_summary_right_var.set(right)
        if hasattr(self, "post_scrub_summary_var"):
            self.post_scrub_summary_var.set(f"{left}\n{right}")


__all__ = ["HMI"]
