SYSTEM_PROMPT = """You are an expert AI technology analyst and technical writer. 
Your task is to synthesize raw news articles, research papers, and software updates into a cohesive, highly readable Daily AI Digest.

Guidelines:
1. ONLY use information provided in the context chunks. Do not hallucinate external facts.
2. Every bullet point or claim MUST include a markdown citation referencing the source URL provided in the context (e.g., [TechCrunch](https://url)). This is a STRICT requirement.
3. Write in a professional, engaging, and concise tone.
4. If a category lacks sufficient information in the context, simply state "No significant updates in this category today."
5. Output valid Markdown format. Use clean headings, bullet points, and bold text for emphasis.
"""

USER_PROMPT_TEMPLATE = """Generate the AI News Pulse Digest for {date}.

Below is the assembled context for each category, retrieved from today's top AI news sources.

{context_chunks}

Format your response STRICTLY according to the following template:

# AI News Pulse - {date}

[A brief, engaging 2-sentence executive summary of the day's most important developments]

## 🤖 LLMs & Foundational Models
[Summarize updates here with citations]

## 🕵️ AI Agents & Automation
[Summarize updates here with citations]

## 🛠️ Tools & Frameworks
[Summarize updates here with citations]

## 💸 Startups & Funding
[Summarize updates here with citations]

## ⚖️ Safety, Ethics & Regulation
[Summarize updates here with citations]

## 🔬 Research Papers
[Summarize updates here with citations]
"""

# These seed queries are used by the vector retriever to find the most relevant chunks in Pinecone
SEED_QUERIES = {
    "llm_models": "New large language models, foundational models, GPT, Claude, Gemini, LLaMA, model releases, benchmark scores.",
    "ai_agents": "AI agents, autonomous agents, multi-agent systems, AI automation, agentic workflows, autonomous execution.",
    "tools_frameworks": "AI developer tools, frameworks, LangChain, LlamaIndex, PyTorch, open source AI libraries, SDK releases.",
    "startups_funding": "AI startup funding, venture capital, series A, seed rounds, acquisitions, mergers in artificial intelligence.",
    "safety_ethics": "AI safety, AI ethics, regulations, AI act, alignment, bias, AI security, deepfakes regulation.",
    "research_papers": "AI research papers, machine learning papers, arXiv, novel architectures, deep learning research, state-of-the-art methods."
}
