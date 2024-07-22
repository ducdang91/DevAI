import requests
import json
import os

from JavaParser import JavaParser
from OpenApi import OpenApi


def extractClassAndMethod(string):
    pairs = []
    elements = string.split(',')
    for element in elements:
        pair = element.split('.')
        class_name = pair[0]
        method_name = None if len(pair) == 1 else pair[1]
        pairs.append((class_name, method_name))
    return pairs


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    mySourceCode = JavaParser()
    # parser.parse_file('C:/Users/duc.dangtrong/source/ASE/SpringBoot/testermatrix/src/main/java/com/asesg/aims/testermatrix/web/product/view/AddUpdateASProductAction.java')
    # mySourceCode.parse_directory('C:/Users/duc.dangtrong/source/ASE/SpringBoot/testermatrix/src/main/java')
    mySourceCode.parse_directory('C:/Users/duc.dangtrong/source/ASE/aims-legacy/old-aims')

    prompt = 'Update ProgramResourceJpaRepository class: add JPA query method to update programResourceStatusId. '
    remind = 'Note that you must response a class/interface with full implementation of updated/added code with no placeholder.  '
    # context = 'AddUpdateHandlerFileForm.load'
    context = 'MachineAction.add'
    pairs = extractClassAndMethod(context)
    print("Pairs of <class name, method name>:")
    request = ''
    for pair in pairs:
        if pair[1]:
            request += mySourceCode.find_method_by_name(pair[0], pair[1])
        else:
            request += mySourceCode.find_class_by_name(pair[0])
    request += '\n' + prompt + remind
    mySourceCode.print_classes_and_methods()
    # print(request)

    # Usage
    openai_api_key = ''  # Put your API key here
    openapi = OpenApi(openai_api_key)

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": request}
    ]

    # response = openapi.call_openai_api(messages)  # None
    # response = None
    # if response:
    #     print("Response from OpenAI:", response)
    #     print('\n')
    #     generated_code = response['choices'][0]['message']['content']
    #     print(generated_code)
    #
    #     # Write the generated code to a file
    #     with open('openapi_resp.java', 'w') as file:
    #         file.write(generated_code)
    #         print("Generated code saved to 'openapi_resp.java'")
    # else:
    #     print("No response received from OpenAI.")
    #
    # # Read and print the content from openapi_resp.java
    # with open('openapi_resp.java', 'r') as file:
    #     generated_code = file.read()
    #     print("Generated code from 'openapi_resp.java':")
    #     print(generated_code)
    # if response:
    #     print("Response from OpenAI:", response)
    #     print('\n')
    #     print(response['choices'][0]['message']['content'])
    # with open('openapi_resp.json', 'w') as json_file:
    #     json.dump(response, json_file)
    #
    # # Read and print the content from openapi_resp.json
    # with open('openapi_resp.json', 'r') as json_file:
    #     loaded_response = json.load(json_file)
    #     print(loaded_response['choices'][0]['message']['content'])