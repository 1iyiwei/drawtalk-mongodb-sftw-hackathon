import voyageai
vo = voyageai.Client()
result = vo.embed("hello world", model="voyage-4-large")
print(result.embeddings)