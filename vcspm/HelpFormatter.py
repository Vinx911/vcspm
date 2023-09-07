import argparse


class HelpFormatter(argparse.HelpFormatter):
    def _format_action_invocation(self, action: argparse.Action) -> str:
        formatted = super()._format_action_invocation(action)
        if action.option_strings and action.nargs != 0:
            formatted = formatted.replace(
                f" {self._format_args(action, self._get_default_metavar_for_optional(action))}",
                "",
                len(action.option_strings) - 1,
            )

        return formatted
