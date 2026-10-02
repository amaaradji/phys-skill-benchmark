from harness.models import client_for, load_config


def main():
    for model_id in load_config()["models"]:
        client, deployment = client_for(model_id)
        response = client.responses.create(model=deployment, input="Reply with exactly: OK")
        print(f"{model_id}: {response.output_text.strip()!r} (served by {response.model})")


if __name__ == "__main__":
    main()
