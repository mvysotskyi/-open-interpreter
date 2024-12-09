from llm_server.llms import LLMSafetyEvaluator
from dotenv import dotenv_values


def main():
    with open('benchmark.txt', 'r') as f:
        bench = f.read()
    bench = bench.split("&&&")
    code_samples = [bench[i].strip() for i in range(len(bench)) if i % 2 == 1]
    results = [bench[i].strip() for i in range(len(bench)) if i % 2 == 0][1:]

    config = dotenv_values(".env")

    safety_evaluator = LLMSafetyEvaluator(api_key=config['OPENAI_API_KEY'])

    positive = 0
    negative = 0
    for i, code in enumerate(code_samples):
        result = safety_evaluator.evaluate(code)
        
        if ((result == 'safe' or result == 'very safe') and results[i].lower() == 'safe') or ((result == 'harmful' or result == 'potentially harmful') and results[i].lower() == 'unsafe'):
            print(f"Passed for code {code}")
            positive += 1
        else:
            print(f"Failed for code {code}. Expected {results[i]}, got {result}")
            negative += 1

    print(f"Passed: {positive}, Failed: {negative}")
    print(f"Accuracy: {positive / (positive + negative) * 100:.2f}%")





if __name__ == '__main__':
    main()