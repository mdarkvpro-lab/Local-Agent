from agent import Agent
from config import MAX_AGENT_STEPS, MODEL, WORKSPACE
from ui import (
    prompt_user,
    separator,
    show_banner,
    show_error,
    show_help,
    show_status,
)


def main():
    agent = Agent()

    show_banner(
        model=MODEL,
        workspace=WORKSPACE,
    )

    while True:
        try:
            user_input = prompt_user()

        except (KeyboardInterrupt, EOFError):
            print()
            separator()
            print("Session closed.")
            break

        user_input = user_input.strip()

        if not user_input:
            continue

        command = user_input.lower()

        # --------------------------------------------------------
        # EXIT
        # --------------------------------------------------------

        if command in {
            "/exit",
            "/quit",
            "exit",
            "quit",
        }:
            separator()
            print("Session closed.")
            break

        # --------------------------------------------------------
        # CLEAR
        # --------------------------------------------------------

        if command in {
            "/clear",
            "clear",
        }:
            show_banner(
                model=MODEL,
                workspace=WORKSPACE,
            )
            continue

        # --------------------------------------------------------
        # HELP
        # --------------------------------------------------------

        if command in {
            "/help",
            "help",
        }:
            show_help()
            continue

        # --------------------------------------------------------
        # STATUS
        # --------------------------------------------------------

        if command in {
            "/status",
            "status",
        }:
            show_status(
                model=MODEL,
                workspace=WORKSPACE,
                step=agent.current_step,
                max_steps=MAX_AGENT_STEPS,
            )
            continue

        # --------------------------------------------------------
        # AGENT
        # --------------------------------------------------------

        try:
            agent.run(user_input)

        except KeyboardInterrupt:
            print()
            show_error("Operation interrupted by user.")

        except Exception as exc:
            show_error(
                f"{type(exc).__name__}: {exc}"
            )


if __name__ == "__main__":
    main()