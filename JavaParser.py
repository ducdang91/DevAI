import re
import os
import sys


class JavaParser:
    def __init__(self):
        self.not_found_methods = []
        self.current_method_multi_line_params = None
        self.log_flag = True
        self.classes = {}
        self.req_classes = {}
        self.current_class = None
        self.class_content = None
        self.current_method_access_modifier = None
        self.current_method_return_type = None
        self.current_method_name = None
        self.current_method_params = []
        self.current_method_body = None
        self.current_class_annotations = []
        self.current_field_method_annotations = []

    def parse_directory(self, directory_path):
        for root, _, files in os.walk(directory_path):
            for file_name in files:
                if file_name.endswith('.java'): # and file_name in ('AdminSessionBean.java', 'MachineAction.java'):
                    file_path = os.path.join(root, file_name)
                    self.parse_file(file_path)

    def parse_file(self, file_path):
        self.current_class = None
        self.current_method_access_modifier = None
        self.current_method_return_type = None
        self.current_method_name = None
        self.current_method_body = None

        self.class_content = ''
        # with open(file_path, 'r') as file:
        #     for line in file:
        #         if not line.startswith('import') and not line.startswith('package'):
        #             self.class_content += line

        with open(file_path, 'r') as file:
            for line in file:
                self.parse_line(line)

    def parse_line(self, line):
        if line == '\n':
            return
        # if 'SetTimeAsNoon' in line:
        #     print('hello')

        class_match = re.search(r'(class|interface)\s+(\w+)', line)
        field_match = re.search(
            r'(?:private|public|protected)\s+(?:static\s+)?(?:final\s+)?(\w+)\s+(\w+)(?:\s*=\s*.+)?;', line)
        # method_match = re.search(r'(private|public|protected)\s+(?:static\s+)?(\w+(?:<.*>)?)\s+(\w+)\s*\((.*)', line)
        method_match = re.search(
            r'(private|public|protected)\s+(?:static\s+)?([\w\\.]+(?:<.*>)?)\s+(\w+)\s*\(([^)]*)\s*',
            line)
        i_method_match = re.search(r'\s+(?:static\s+)?(\w+(?:<.*>)?)\s+(\w+)\s*\((.*)\);', line)
        is_interface_method = self.current_class and ('JpaRepository' in self.current_class
                                                      or self.current_class.endswith('Service'))
            
        if line.startswith("@") and not self.current_class:
            self.handle_class_annotation(line)
        if line.startswith("    @") and self.current_class:
            self.handle_field_or_method_annotation(line)
        elif class_match and self.current_class is None:
            self.handle_class_or_interface(class_match)
        elif field_match:
            self.handle_field(field_match)
        elif method_match:
            self.handle_method_begin(method_match, line)
        elif is_interface_method and i_method_match:
            self.handle_interface_method_begin(i_method_match)
        elif self.current_method_multi_line_params:
            self.handle_method_multi_line_params(line)
        elif self.current_method_body is not None and line != '    }\n':
            self.current_method_body.append(line)
        elif self.current_method_body is not None and line == '    }\n':
            self.current_method_body.append(line)
            self.handle_method_body_end()

    def handle_class_or_interface(self, match):

        class_name = match.group(2)
        self.classes[class_name] = {'content': self.class_content, 'fields': [], 'methods': {}, 'annotations': self.current_class_annotations}
        self.current_class = class_name
        self.current_class_annotations = []

    def handle_class_annotation(self, annotaion):
        self.current_class_annotations.append(annotaion)

    def handle_field_or_method_annotation(self, annotaion):
        self.current_field_method_annotations.append(annotaion)

    def handle_field(self, match):
        field_type = match.group(1)
        field_name = match.group(2)
        if self.current_class:
            self.classes[self.current_class]['fields'].append(
                (self.current_field_method_annotations, field_type, field_name))
        self.current_field_method_annotations = []

    def add_method_params_as_fields(self, params_line):
        # Extract parameters from params_line
        if self.current_class:
            parameters = re.findall(r'(?:@\w+\s+)?(\w+)(?:<.*>)?(?:\.\.\.)?\s+(\w+)', params_line)
            for parameter in parameters:
                field_type, field_name = parameter
                self.classes[self.current_class]['fields'].append(([], field_type, field_name))
                self.current_method_params.append(parameter)

    def handle_method_begin(self, match, line):
        self.current_method_access_modifier = match.group(1)
        self.current_method_return_type = match.group(2)
        self.current_method_name = match.group(3)
        # self.current_method_params = match.group(4)
        self.current_method_body = []
        # print(f'{self.current_class}: {line}')

        self.add_method_params_as_fields(match.group(4))
        if ')' not in line:
            self.current_method_multi_line_params = True

    def handle_interface_method_begin(self, match):
        self.add_method_params_as_fields(match.group(3))
        method = match.group(2)
        if method in self.classes[self.current_class]['methods']:
            self.classes[self.current_class]['methods'][method].append((None, match.group(1), match.group(2),
                                                                        self.current_method_params, None))
        else:
            self.classes[self.current_class]['methods'][method] = [(None, match.group(1), match.group(2),
                                                                    self.current_method_params, None)]
        self.current_method_body = None
        self.current_method_params = []

    def handle_method_multi_line_params(self, line):
        self.add_method_params_as_fields(line)
        if ')' in line:
            self.current_method_multi_line_params = False

    def handle_method_body_end(self):
        method_fields = re.findall(r'(\w+)\s+(\w+)(?:\s*=\s*.+)?;', ''.join(self.current_method_body))
        for field_type, field_name in method_fields:
            self.classes[self.current_class]['fields'].append(([], field_type, field_name))

        if self.current_method_name in self.classes[self.current_class]['methods']:
            (self.classes[self.current_class]['methods'][self.current_method_name]
             .append((self.current_method_access_modifier, self.current_method_return_type,
                        self.current_method_name, self.current_method_params, self.current_method_body)))
        else:
            self.classes[self.current_class]['methods'][self.current_method_name] = \
                [(self.current_method_access_modifier, self.current_method_return_type,
                    self.current_method_name, self.current_method_params, self.current_method_body)]
        self.current_method_body = None
        self.current_method_params = []

    def get_method_params_as_string(self, method_params):
        params_str = ''
        for param_type, param_name in method_params:
            params_str = params_str + f'{param_type} {param_name}, '

        if params_str:
            return params_str[:-2]
        return params_str
    def print_parsed_methods(self):
        for class_name, class_data in self.classes.items():
            print(f'{class_name}:')
            print('Fields:')
            for field_type, field_name in class_data['fields']:
                print(f'    {field_type} {field_name}')
            print('Methods:')
            for access_modifier, return_type, method_name, method_params, method_body in class_data['methods']:
                print(f'    {access_modifier} {return_type} {method_name}({self.get_method_params_as_string(method_params)}){{')
                # for line in method_body:
                #     print(f'{line}')
                # print('    }')

    def extract_classes_and_methods(self, class_name, method_body):
        if not method_body:
            return

        for line in method_body:
            innerClassMethods = re.findall(r'\b(\w+)\s*\(', line)
            outerClassMethods = re.findall(r'\b(\w+)\.(\w+)\s*\(', line)
            if outerClassMethods:
                for outerClassName, outerMethodName in outerClassMethods:
                    if 'Service' in outerClassName:
                        self.find_method_by_name(f'{self.capitalize_first_char(outerClassName)}Impl', outerMethodName)
                    else:
                        self.find_method_by_name(f'{self.capitalize_first_char(outerClassName)}', outerMethodName)

            for inSameClassMethod in innerClassMethods:
                if inSameClassMethod not in [method[1] for method in outerClassMethods]:
                    self.find_method_by_name(f'{class_name}', inSameClassMethod)

        # method_calls1 = re.findall(r'(\w+)\.(\w+)\(', ''.join(method_body))
        # method_calls2 = re.findall(r' (\w+)\(', ''.join(method_body))
        # if method_calls2:
        #     for method_name in method_calls2:
        #         method_calls1.append((class_name, method_name))
        #
        # for field_name, method_name in method_calls1:
        #     if self.log_flag:  # Check if log_flag is true
        #         print(f'// {class_name} {field_name}.{method_name}')
        #     field_class_name = None
        #     if (field_name[0].isupper()):
        #         field_class_name = field_name
        #     elif class_name in self.classes:  # Check if current_class exists in parsed classes
        #         for field_annotations, field_type, field_name_candidate in self.classes[class_name]['fields']:
        #             if field_name_candidate == field_name:
        #                 field_class_name = field_type  # If field_name matches, assign current_class to class_name
        #                 break
        #     if field_class_name:
        #         # print(f"// Class: {field_class_name}, Method: {field_class_name}.{method_name}")
        #         if 'Service' in field_class_name:
        #             self.find_method_by_name(f'{field_class_name}Impl', method_name)
        #         else:
        #             self.find_method_by_name(field_class_name, method_name)
        #             if 'Repository' in field_class_name:
        #                 self.find_method_by_name(f'{field_class_name}Impl', method_name)
        #
        #     else:
        #         if self.log_flag:  # Check if log_flag is true
        #             print(f"// Field '{field_name}' not found in class '{class_name}'.")

    def capitalize_first_char(self, input_string):
        if not input_string:
            return input_string  # Return the original string if it's empty or None
        return input_string[0].upper() + input_string[1:]

    def print_method_body(self, method_body):
        for line in method_body:
            sys.stdout.write(line)

    def find_method_by_name(self, class_name, method_name):
        if class_name in self.req_classes and method_name in self.req_classes[class_name]['methods']:
            return

        if class_name in self.classes:
            if method_name in self.classes[class_name]['methods']:
                for access_modifier, return_type, name, params, body in self.classes[class_name]['methods'][method_name]:
                # if name == method_name:
                    # print(f'// Class {class_name} has method:')
                    # print(f'{access_modifier} {return_type} {name}({self.get_method_params_as_string(params)}) {{')
                    # self.print_method_body(body)
                    method_content = f'{access_modifier} {return_type} {name}({self.get_method_params_as_string(params)})'
                    if body:
                        method_content += ' {\n'
                        method_content += ''.join(body)  # Append method body
                    else:
                        method_content += ';'

                    method_and_params = f'{name} {self.get_method_params_as_string(params)}'

                    if class_name in self.req_classes:
                        if method_name in self.req_classes[class_name]['methods']:
                            self.req_classes[class_name]['methods'][method_name].append((method_and_params, method_content))
                        else:
                            self.req_classes[class_name]['methods'][method_name] = [(method_and_params, method_content)]
                    else:
                        self.req_classes[class_name] = {'methods': {}}
                        self.req_classes[class_name]['methods'][method_name] = [(method_and_params, method_content)]

                    # if self.log_flag:
                    #     print(f"{class_name} class has {method_name} method:")
                    #     print(f"{method_content}")
                    self.extract_classes_and_methods(class_name, body)  # Call the method to extract classes and methods
                    return method_content
            elif self.log_flag:
                not_found_method = f"// Method '{method_name}' not found in class '{class_name}'."
                if not_found_method not in self.not_found_methods:
                    self.not_found_methods.append(not_found_method)
                    print(not_found_method)

    def generate_java_code(self):
        java_code = ""
        for class_name, class_info in self.req_classes.items():
            java_code += f"class {class_name} {{\n"
            for method_name, methods in class_info['methods'].items():
                for method_and_params, method_content in methods:
                    java_code += method_content
            java_code += "}\n"
        return java_code

    def print_classes_and_methods(self):
        return print(self.generate_java_code())
    def find_class_by_name(self, class_name):
        return self.classes[class_name]['content']


if __name__ == "__main__":
    parser = JavaParser()
    # parser.parse_file('C:/Users/duc.dangtrong/source/ASE/SpringBoot/testermatrix/src/main/java/com/asesg/aims/testermatrix/web/product/view/AddUpdateASProductAction.java')
    # parser.parse_directory('C:/Users/duc.dangtrong/source/ASE/SpringBoot/testermatrix/src/main/java')
    parser.parse_directory('C:/Users/duc.dangtrong/source/Java/food-ordering-system')

    # parser.print_parsed_methods()
    class_name = 'OrderController' #input("Enter the class name: ")
    method_name = 'createOrder' #input("Enter the method name: ")

    # Find method_name in class_name and print it's method body to screen
    parser.find_method_by_name(class_name, method_name)
