# LLM-based Learning Companion & Co-pilot 

In this project, the student is expected to propose, design, and develop a Chatbot or QnA Agent for courses that cater to large groups (i.e. > 500) of learners and participants. Given a set of pre-defined external resources i.e. ebooks, web links, APIs, as well as internal course materials, the agent will be able to answer course content, guides, and exercises matters. The agent should also act as an auto-tutor which is capable of answering queries related to the course content by providing examples, explanations, or illustrations from within or external resources. The agent will only redirect the query to the instructors via email when in doubt or unable to answer the query confidently. Generally, students taking up this project will analyze, explore, evaluate, and employ QnA Chatbot for the project design and development. The student can customize and consider incorporating other advanced technologies / APIs that are deemed useful for this purpose. The student taking up this project should possess a good understanding and skillset to work with LangChain and also various Microsoft Azure cloud services. 

---

## Table of Contents

1. [Requirements](#requirements)
2. [Environment Setup](#environment-setup)
3. [How to Run](#how-to-run)

---

### Requirements
The platform requires the following Python packages, which are listed in the `requirements.txt` file. Please make sure to create a virtual environment before installing the requirements.

For windows:
```bash
# Create a virtual environment named 'venv'
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

For mac:
```bash
# Create a virtual environment named 'venv'
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### Environment Setup
Ensure the following environment variables are properly configured in a `.env` file to run locally. You will need to fill up the required secret keys from `.env.example` and rename it accordingly. For cloud deployment, the environment variables will need to passed into your cloud provider. The report deployed on Microsoft Azure through the Web App Service.

---

### How to Run
To start the platform:

1. Ensure all environment variables are configured in a `.env` file.
2. Start the application using Streamlit:

```bash
streamlit run main.py
```
