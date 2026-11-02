from __future__ import annotations

from emporio_agent.agent import AgentError, EmporioAgent
from emporio_agent.bootstrap import build_application


def main() -> None:
    application = build_application()
    try:
        agent = EmporioAgent(application.settings, application.tools)
    except AgentError as error:
        raise SystemExit(str(error)) from error

    history: list[dict[str, str]] = []
    print("Empório da Música — digite 'sair' para encerrar.")
    while True:
        try:
            message = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if message.casefold() in {"sair", "exit", "quit"}:
            break
        if not message:
            continue
        response = agent.chat(message, history)
        print(f"Assistente: {response.answer}")
        history.extend(
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": response.answer},
            ]
        )


if __name__ == "__main__":
    main()
