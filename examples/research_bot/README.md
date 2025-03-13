# Enhanced Research Bot

A powerful multi-agent system for conducting in-depth research on any topic. This research bot uses specialized agents to plan searches, gather information, evaluate content, and generate comprehensive research reports with proper citations and scientific formatting.

## Features

- **Multi-agent Architecture**: Utilizes specialized agents for different research tasks
- **Multiple Research Types**: Support for scientific, technical, humanities, and interdisciplinary research
- **Web & File Search**: Searches both the web and local files for comprehensive information gathering
- **Quality Assessment**: Built-in quality evaluation and iterative refinement of research reports
- **Scientific Standards**: Reports meet academic and scientific standards with proper formatting
- **Citation Management**: Automatic handling and normalization of references
- **Custom Research Output**: Markdown and plain text output formats with organized sections

## Setup

### Prerequisites

- Python 3.10 or higher
- OpenAI API key

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/blackpandachan/openai-agents-python.git
   cd openai-agents-python
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # On Windows
   python -m venv env
   .\env\Scripts\activate

   # On macOS/Linux
   python -m venv env
   source env/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e .
   ```

4. **Set up environment variables**:
   
   Create a `.env` file in the `examples` directory:
   ```bash
   touch examples/.env
   ```
   
   Add your OpenAI API key to the `.env` file:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
   
   Alternatively, you can set it as an environment variable:
   ```bash
   # On Windows
   set OPENAI_API_KEY=your_api_key_here
   
   # On macOS/Linux
   export OPENAI_API_KEY=your_api_key_here
   ```

## Usage

### Running the Research Bot

There are multiple ways to run the research bot:

1. **As a module**:
   ```bash
   python -m examples.research_bot
   ```

2. **Using the run script**:
   ```bash
   python examples/research_bot/run_research.py
   ```

3. **Using the example runner**:
   ```bash
   python examples/run_research_bot.py
   ```

### Command-line Arguments

The research bot accepts several command-line arguments:

- `--query`: Research topic (if not provided, will prompt interactively)
- `--search-type`: Type of search to perform (`web`, `file`, or `web_and_file`, default: `web_and_file`)
- `--max-iterations`: Maximum number of refinement iterations (default: 3)
- `--min-quality`: Minimum quality score threshold (default: 8.5)

Example:
```bash
python -m examples.research_bot --query "History of quantum computing" --search-type web --max-iterations 2
```

## Architecture

The Enhanced Research Bot uses a sophisticated multi-agent architecture:

1. **Research Router Agent**: Determines the appropriate research type (scientific, technical, humanities, interdisciplinary)

2. **Planner Agent**: Develops a strategic plan for information gathering with specific search queries

3. **Search Agents**: Execute web searches based on the plan and summarize findings (run in parallel)

4. **File Search Agent**: Searches local files for relevant information (optional)

5. **Specialized Research Agents**:
   - Scientific Research Agent
   - Technical Research Agent
   - Humanities Research Agent
   - Interdisciplinary Research Agent

6. **Evaluator Agents**:
   - Quality Evaluator: Assesses the overall research quality
   - Scientific Standards Evaluator: Ensures adherence to scientific standards

7. **Report Refinement System**: Iteratively improves reports based on evaluator feedback

## Output Files

Research results are saved in the `research_output` directory with the following files:

- `research_[Topic]_[Timestamp].md`: Final research report in Markdown format
- `raw_agent_output_[Timestamp].txt`: Raw output from the research agents
- `TechnicalResearchAgentTrace.json`: Trace of the agent's reasoning process (for debugging)

## Suggested Improvements & Customization

The research bot is designed to be extensible. Here are some ways to further enhance it:

1. **Custom Knowledge Base**: Connect to your organization's knowledge base or private documents
2. **Domain-specific Agents**: Add specialized agents for medicine, law, engineering, etc.
3. **Interactive Refinement**: Add user feedback loops during the research process
4. **Output Formats**: Generate reports in different formats (PDF, LaTeX, etc.)
5. **Visualization**: Add data visualization capabilities for technical research topics

## Troubleshooting

- **API Key Issues**: Ensure your OpenAI API key is correctly set in the `.env` file or as an environment variable
- **Import Errors**: Make sure you've installed the package with `pip install -e .`
- **File Search Errors**: Verify that the directory you're searching exists and is accessible
- **Output Errors**: Check that the `research_output` directory exists and is writable

## License

This project is licensed under the terms specified in the main repository.
