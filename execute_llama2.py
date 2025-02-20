import os
import re
import json
import requests

OUTPUT_PATH = "Output"
architecture_data = None

# Local LLaMA 2 API server address
LLAMA_API_URL = "http://localhost:11434/api/generate"

def extract_json(text):
    """
    Extract JSON code block from LLaMA 2 API response and attempt to fix its structure.
    """
    json_match = re.search(r"(\{[\s\S]*\})", text)

    if json_match:
        json_text = json_match.group(1)  # Extract matched JSON snippet

        try:
            return json.loads(json_text)  # Attempt to parse JSON directly
        except json.JSONDecodeError:
            print("⚠️ JSON parsing failed, attempting to fix JSON structure...")
            return fix_json_structure(json_text)
    else:
        print("❌ Error: No JSON block found! Original response:")
        print(text)
        return None

def fix_json_structure(json_text):
    """
    Fix JSON structure:
    - Remove extra commas before list elements.
    - Ensure proper key-value formatting.
    - Close unbalanced `{}` and `[]`.
    """
    try:
        # Remove Markdown code block markers if present
        json_text = json_text.strip().strip("```json").strip("```")

        # Remove misplaced commas before elements
        json_text = re.sub(r",\s*([\]}])", r"\1", json_text)  # Remove trailing commas before `}` or `]`
        json_text = re.sub(r"\[\s*,", "[", json_text)  # Remove extra `[,]`

        # Ensure valid JSON structure
        open_braces, close_braces = json_text.count("{"), json_text.count("}")
        open_brackets, close_brackets = json_text.count("["), json_text.count("]")

        if open_braces > close_braces:
            json_text += "}" * (open_braces - close_braces)
        if close_braces > open_braces:
            json_text = "{" * (close_braces - open_braces) + json_text

        if open_brackets > close_brackets:
            json_text += "]" * (open_brackets - close_brackets)
        if close_brackets > open_brackets:
            json_text = "[" * (close_brackets - open_brackets) + json_text

        # Attempt to parse JSON
        return json.loads(json_text)

    except json.JSONDecodeError:
        print("❌ Error: JSON structure could not be fixed. Final JSON:")
        print(json_text)
        return None



def ask_llama_for_architecture(software_description):
    payload = {
        "model": "llama2",
        "prompt": (
            "You are an expert software architect. "
            "Given a software description, propose a high-level architecture. "
            "Provide a JSON response **only** (no explanations or extra text) with the following keys:\n\n"
            "software_architecture: A high-level architecture description.\n"
            "technical_stacks: A list of technologies to be used.\n"
            "file_scaffolding: A structured overview of files and their purposes.\n"
            "number_of_files: The total number of files.\n"
            "number_of_prompts: Estimated prompts needed to generate the software.\n"
            f"Here is the software description:\n{software_description}\n"
            "Return **only valid JSON** without explanations, Markdown, or extra text."
        ),
        "stream": False,
        "options": {
            "num_ctx": 512  # Increase context window to reduce truncation
        }
    }
    try:
        response = requests.post(LLAMA_API_URL, json=payload)

        if response.status_code == 200:
            raw_text = response.json().get("response", "")
            json_data = extract_json(raw_text)
            return json_data

        else:
            print(f"❌ Error while asking LLaMA 2: HTTP {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error: {e}")
    return None

def main():
    software_description = input("Enter the software system description:\n> ")
    global architecture_data
    architecture_data = ask_llama_for_architecture(software_description)

    if not architecture_data:
        print("❌ Could not retrieve a valid architecture proposal. Exiting.")
        return

    print("\n✅ Retrieved software architecture proposal:")
    print(json.dumps(architecture_data, indent=2, ensure_ascii=False))

    user_input = input("\nDo you accept this architecture proposal? (yes/no): ").strip().lower()
    if user_input not in ["yes", "y"]:
        print("❌ Architecture not accepted. Exiting.")
        return

    print("✅ Architecture accepted. Generating files...")
    generate_software_files()
    print("\n✅ All files have been generated. Check the 'Output' folder.")

def generate_software_files():
    if not architecture_data:
        print("❌ Error: No architecture data available for file generation.")
        return

    os.makedirs(OUTPUT_PATH, exist_ok=True)
    file_scaffolding = architecture_data.get("file_scaffolding", [])

    if isinstance(file_scaffolding, dict):
        file_scaffolding = [{"name": key, "content": value.get("content", "")} for key, value in file_scaffolding.items()]

    if not isinstance(file_scaffolding, list):
        print("❌ Error: file_scaffolding is not a list!")
        return

    for file in file_scaffolding:
        if not isinstance(file, dict):
            print(f"⚠️ Skipping invalid file entry: {file} (not a dictionary)")
            continue

        filename = file.get("name", "unnamed_file.txt")
        content = file.get("content", "")
        folder = os.path.dirname(filename)

        folder_path = os.path.join(OUTPUT_PATH, folder) if folder else OUTPUT_PATH
        os.makedirs(folder_path, exist_ok=True)
        save_file_to_output(folder_path, os.path.basename(filename), content)

def save_file_to_output(folder, filename, content):
    file_path = os.path.join(folder, filename)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📁 File generated: {file_path}")
    except Exception as e:
        print(f"❌ Error saving file {file_path}: {e}")

if __name__ == "__main__":
    main()
