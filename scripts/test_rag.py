from modules.rag_pipeline import generate_answer

question = "How many unemployment days are allowed during post-completion OPT?"

result = generate_answer(question)

print("\nQUESTION:")
print(result["query"])

print("\nANSWER:")
print(result["answer"])

print("\nSOURCES:")
for source in result["sources"]:
    print("-", source["source_title"])
    print(source["source_url"])

print("\nHALLUCINATION ANALYSIS:")
print(result["hallucination_analysis"])

print("\nRISK ANALYSIS:")
print(result["risk_analysis"])