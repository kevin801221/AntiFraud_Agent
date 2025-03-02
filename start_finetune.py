from openai import OpenAI
import os

client = OpenAI()

# First, upload the file
with open("fraud_data/03_training_data/formatted_training_data_openai.jsonl", "rb") as file:
    response = client.files.create(
        file=file,
        purpose="fine-tune"
    )
file_id = response.id

# Create fine-tuning job
job = client.fine_tuning.jobs.create(
    training_file=file_id,
    model="gpt-4o-mini-2024-07-18",  # or "gpt-3.5-turbo-0125"
    method={
        "type": "supervised",
        "supervised": {
            "hyperparameters": {"n_epochs": 3}  # Adjust epochs as needed
        },
    }
)

print(f"Fine-tuning job created: {job.id}")

# You can monitor the job status
job_status = client.fine_tuning.jobs.retrieve(job.id)
print(f"Job status: {job_status.status}")
