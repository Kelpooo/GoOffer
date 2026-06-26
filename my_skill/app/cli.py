import argparse
import json

from my_skill.collectors.wechat_window_collector import collect_wechat_window_chat


def cmd_collect_wechat_window(args):
    result = collect_wechat_window_chat(
        output_path=args.output,
        rounds=args.rounds,
        delay=args.delay,
        startup_delay=args.startup_delay,
        pageup_presses=args.pageup_presses,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="My Skill CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser(
        "collect-wechat-window",
        help="Collect visible chat text from current WeChat window",
    )
    collect_parser.add_argument("--output", required=True, help="Merged text output path")
    collect_parser.add_argument("--rounds", type=int, default=10, help="How many copy-scroll rounds to run")
    collect_parser.add_argument("--delay", type=float, default=3.5, help="Delay between copy and next scroll")
    collect_parser.add_argument("--startup-delay", type=int, default=5, help="Seconds to switch to WeChat before capture starts")
    collect_parser.add_argument("--pageup-presses", type=int, default=8, help="How many PageUp key presses between rounds")
    collect_parser.set_defaults(func=cmd_collect_wechat_window)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
