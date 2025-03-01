# AntiFraud Agent

This project implements an AI-powered fraud detection system that learns from real-world fraud cases to help prevent future scams.

## Data Collection and Training Process

The training data is collected through the following pipeline:

1. **Web Crawling**: Using the JinaCrawler component, we crawl fraud case information from the Taiwan National Police Agency's Anti-Fraud website (165.npa.gov.tw). This provides us with real-world fraud cases and prevention information.

2. **Content Processing**: The ContentProcessor component processes the crawled data, cleaning and structuring the raw HTML content into meaningful fraud case information.

3. **Training Data Generation**: The TrainingDataGenerator transforms the processed content into a format suitable for training reinforcement learning models. This includes:
   - Extracting fraud patterns and techniques
   - Identifying scammer behaviors and tactics
   - Capturing victim responses and outcomes
   - Generating appropriate counter-measures and prevention strategies

## Project Structure

- `core/`: Core components of the system
  - `jina_crawler.py`: Web crawler for collecting fraud case data
  - `content_processor.py`: Processes and structures raw crawled content
  - `training_data_generator.py`: Generates training data for the AI model
  - `utils.py`: Utility functions used across the system
- `main.py`: Main entry point for running the data pipeline

## Setup

1. Clone the repository:
```bash
git clone https://github.com/kevin801221/AntiFraud_Agent.git
cd AntiFraud_Agent
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables:
- Copy `.env.example` to `.env`
- Fill in your API keys in `.env`:
  ```
  JINA_API_KEY=your_jina_api_key_here
  OPENAI_API_KEY=your_openai_api_key_here
  ```

## Usage

Run the data pipeline:
```bash
python main.py
```

This will:
1. Crawl fraud cases from specified URLs
2. Process the crawled content
3. Generate training data in the `fraud_data/03_training_data` directory

## Note

This project focuses on collecting and processing fraud-related data for training AI models. The actual model training code is not included in this repository.
