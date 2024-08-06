import re
import os
import sys
import pickle


class JavaParser:
    def __init__(self):
        self.not_found_messages = []
        self.current_method_multi_line_params = None
        self.log_flag = True
        self.tab = None
        self.classes = {}
        self.classes_package = {}
        self.req_classes = {}
        self.current_class = None
        self.current_package = None
        self.current_imports = {}
        self.class_content = None
        self.current_method_access_modifier = None
        self.current_method_return_type = None
        self.current_method_name = None
        self.current_method_params = []
        self.current_method_body = None
        self.current_method_fields = {}
        self.current_class_annotations = []
        self.current_field_method_annotations = []

        self.field_or_method_annotation_start = False
        self.class_annotation_start = False
        self.ignored_methods = ('if', 'catch', 'Exception', 'equals', 'replaceAll', 'for', 'get', 'setHint',
                                'getStackTrace', 'log', 'Exception', 'for', 'getLogger', 'log', 'getId', 'replaceAll',
                                'isEmpty', 'find', 'trim')
        self.files_to_check = None
        # self.files_to_check = ['QualificationAction.java']
        # self.files_to_check = ['QualificationAction.java', 'Setup.java', 'ProductTraveller.java', 'ProductTravellerSession.java']

    def parse_directory(self, directory_path):
        saved_classes_file_path = os.path.join(os.getcwd(), os.path.basename(directory_path) + '-classes.txt')
        if self.files_to_check is None:
            self.load_from_file(saved_classes_file_path)
        if self.classes == {}:
            for root, _, files in os.walk(directory_path):
                for file_name in files:
                    if self.files_to_check is not None and file_name in self.files_to_check:
                        file_path = os.path.join(root, file_name)
                        self.parse_file(file_path)
                    if self.files_to_check is None and file_name.endswith('.java'):
                        file_path = os.path.join(root, file_name)
                        self.parse_file(file_path)
            self.save_to_file(saved_classes_file_path)

    def parse_file(self, file_path):
        self.current_class = None
        self.current_package = None
        self.current_imports = {}
        self.current_method_access_modifier = None
        self.current_method_return_type = None
        self.current_method_name = None
        self.current_method_body = None
        self.field_or_method_annotation_start = False
        self.class_annotation_start = False
        self.tab = None

        self.class_content = ''
        # with open(file_path, 'r') as file:
        #     for line in file:
        #         if not line.startswith('import') and not line.startswith('package'):
        #             self.class_content += line

        with open(file_path, 'r') as file:
            for line in file:
                if line.startswith('package'):
                    self.current_package = re.search(r'package\s+([\w\\.]+);', line).group(1)
                elif line.startswith('import'):
                    import_match = re.search(r'import\s+([\w\\.]+)\.(\w+);', line)
                    if import_match:
                        self.current_imports[import_match.group(2)] = import_match.group(1)
                else:
                    self.class_content += line
                    self.parse_line(line)

        if self.current_class:
            self.classes[self.current_class]['content'] = self.class_content
            self.classes[self.current_class]['imports'] = self.current_imports

    def parse_line(self, line):
        if line == '\n':
            return
        if 'void changeCurrentTravellerState' in line and self.files_to_check:
            print(f'Check {line}')
        # // Add fields to methods, not class
        class_match = re.search(r'(class|interface)\s+(\w+)', line)
        field_match = re.search(
            r'(?:private|public|protected)\s+(?:static\s+)?(?:final\s+)?(\w+(?:<[\w<>]+>)?)\s+(\w+)\s*(?:=\s*new\s+\w+\s*\([^;]*\))?\s*;', line)
        constructor_match = re.search(r'(\w+)\s+(\w+)\s*=\s*new', line)
        var_assign_match = re.search(r'(\w+)\s+(\w+)\s*=', line)
        var_define_match = re.search(r'(\w+)\s+(\w+)\s*;', line)
        forloop_var_match = re.search(r'for \((\w+) (\w+) :', line)
        # method_match = re.search(r'(private|public|protected)\s+(?:static\s+)?(\w+(?:<.*>)?)\s+(\w+)\s*\((.*)', line)
        method_match = re.search(
            r'(private|public|protected)\s+(?:static\s+)?([\w\\.]+(?:<.*>)?)\s+(\w+)\s*\(([^)]*)\s*',
            line)
        i_method_match = re.search(r'\s+(?:static\s+)?(\w+(?:<.*>)?)\s+(\w+)\s*\((.*)\);', line)
        is_interface_method = self.current_class and ('JpaRepository' in self.current_class
                                                      or self.current_class.endswith('Service'))

        if line.startswith("@") and not self.current_class:
            self.handle_class_annotation(line)
            self.class_annotation_start = True
        elif class_match and self.current_class is None:
            self.class_annotation_start = False
            self.handle_class_or_interface(class_match)
        elif self.class_annotation_start:
            self.handle_class_annotation(line)
        elif line.startswith(f'{self.tab}@') and self.current_class:
            self.handle_field_or_method_annotation(line)
            self.field_or_method_annotation_start = True

        # field annotation and field declaration can be in the same line
        if field_match:
            if self.tab is None and line.startswith('    '):
                self.tab = '    '
            elif self.tab is None and line.startswith('  '):
                self.tab = '  '
            self.handle_field(field_match)
            self.field_or_method_annotation_start = False
        elif constructor_match:
            self.handle_method_field(constructor_match)
            if self.current_method_body is not None and line != f'{self.tab}}}\n':
                self.current_method_body.append(line)
        elif var_assign_match:
            self.handle_method_field(var_assign_match)
            if self.current_method_body is not None and line != f'{self.tab}}}\n':
                self.current_method_body.append(line)
        elif var_define_match:
            self.handle_method_field(var_define_match)
            if self.current_method_body is not None and line != f'{self.tab}}}\n':
                self.current_method_body.append(line)
        elif forloop_var_match:
            self.handle_method_field(forloop_var_match)
            if self.current_method_body is not None and line != f'{self.tab}}}\n':
                self.current_method_body.append(line)
        elif method_match:
            self.field_or_method_annotation_start = False
            self.handle_method_begin(method_match, line)
        elif self.field_or_method_annotation_start:
            self.handle_field_or_method_annotation(line)
        elif is_interface_method and i_method_match:
            self.handle_interface_method_begin(i_method_match)
        elif self.current_method_multi_line_params:
            self.handle_method_multi_line_params(line)
        elif self.current_method_body is not None and line != f'{self.tab}}}\n':
            self.current_method_body.append(line)
        elif self.current_method_body is not None and line == f'{self.tab}}}\n':
            self.current_method_body.append(line)
            self.handle_method_body_end()

    def handle_class_or_interface(self, match):
        class_name = match.group(2)
        if self.current_package is not None:
            if class_name not in self.classes_package:
                self.classes_package[class_name] = []
            self.classes_package[class_name].append(self.current_package)

        self.current_class = f"{self.current_package}.{class_name}"
        self.classes[self.current_class] = {'content': self.class_content, 'imports': {}, 'fields': {}, 'methods': {},
                                            'method_fields': {},'annotations': self.current_class_annotations}
        self.current_class_annotations = []

    def handle_class_annotation(self, annotaion):
        self.current_class_annotations.append(annotaion)

    def handle_field_or_method_annotation(self, annotaion):
        self.current_field_method_annotations.append(annotaion)

    def handle_field(self, match):
        field_type = match.group(1)
        field_name = match.group(2)
        if self.current_class and field_name not in self.classes[self.current_class]['fields']:
            self.classes[self.current_class]['fields'][field_name] = (self.current_field_method_annotations, field_type)
        self.current_field_method_annotations = []

    def handle_method_field(self, match):
        field_type = match.group(1)
        field_name = match.group(2)
        if self.current_method_name is not None:
            self.current_method_fields[field_name] = field_type

    def add_method_params_as_fields(self, params_line):
        # Extract parameters from params_line
        if self.current_class:
            parameters = re.findall(r'(?:@\w+\s+)?(\w+)(?:<.*>)?(?:\.\.\.)?\s+(\w+)', params_line)
            for parameter in parameters:
                field_type, field_name = parameter
                self.current_method_fields[field_name] = field_type
                # self.classes[self.current_class]['fields'][field_name] = ([], field_type)
                self.current_method_params.append(parameter)

    def handle_method_begin(self, match, line):
        self.current_method_access_modifier = match.group(1)
        self.current_method_return_type = match.group(2)
        self.current_method_name = match.group(3)
        # self.current_method_params = match.group(4)
        self.current_method_body = []
        self.current_field_method_annotations = []
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
        # method_fields = re.findall(r'(\w+)\s+(\w+)(?:\s*=\s*.+)?;', ''.join(self.current_method_body))
        # for field_type, field_name in method_fields:
        #     self.classes[self.current_class]['fields'][field_name] = ([], field_type)

        if self.current_method_name in self.classes[self.current_class]['methods']:
            (self.classes[self.current_class]['methods'][self.current_method_name]
             .append((self.current_method_access_modifier, self.current_method_return_type,
                      self.current_method_name, self.current_method_params, self.current_method_body)))
        else:
            self.classes[self.current_class]['methods'][self.current_method_name] = \
                [(self.current_method_access_modifier, self.current_method_return_type,
                  self.current_method_name, self.current_method_params, self.current_method_body)]

        if self.current_method_fields:
            if self.current_method_name not in self.classes[self.current_class]['method_fields']:
                self.classes[self.current_class]['method_fields'][self.current_method_name] = self.current_method_fields
            else:
                self.classes[self.current_class]['method_fields'][self.current_method_name].update(self.current_method_fields)

        self.current_method_body = None
        self.current_method_name = None
        self.current_method_params = []
        self.current_method_fields = {}

    def get_method_params_as_string(self, method_params):
        params_str = ''
        for param_type, param_name in method_params:
            params_str = params_str + f'{param_type} {param_name}, '

        if params_str:
            return params_str[:-2]
        return params_str

    # def print_parsed_methods(self):
    #     for class_name, class_data in self.classes.items():
    #         print(f'{class_name}:')
    #         print('Fields:')
    #         for field_type, field_name in class_data['fields']:
    #             print(f'    {field_type} {field_name}')
    #         print('Methods:')
    #         for access_modifier, return_type, method_name, method_params, method_body in class_data['methods']:
    #             print(f'    {access_modifier} {return_type} {method_name}({self.get_method_params_as_string(method_params)}){{')
    #             # for line in method_body:
    #             #     print(f'{line}')
    #             # print('    }')

    def extract_classes_and_methods(self, class_name, method_name, method_body):
        if not method_body:
            return

        for line in method_body:
            # if 'holdReasonServer.' in line:
            #     print('Check method name: ', line)
            innerClassMethods = re.findall(r'\b(\w+)\s*\(', line)
            outerClassMethods = re.findall(r'\b(\w+)\.(\w+)\s*\(', line)
            if outerClassMethods:
                for outerClassName, outerMethodName in outerClassMethods:
                    # if 'adminBean' in outerClassName:
                    #     print('Check class name: ', outerClassName)
                    if 'substring' in outerMethodName:
                        print('Check method name: ', line)
                    field_type, field_field_type = None, None
                    if (method_name in self.classes[class_name]['method_fields']
                            and outerClassName in self.classes[class_name]['method_fields'][method_name]):
                        field_type = self.classes[class_name]['method_fields'][method_name][outerClassName]
                    elif outerClassName in self.classes[class_name]['fields']:
                        field_type = self.classes[class_name]['fields'][outerClassName]

                    if 'Service' in outerClassName:
                        self.find_method_by_name(f'{self.capitalize_first_char(outerClassName)}Impl', outerMethodName)
                    elif field_type is not None:
                        lombok_field = False
                        if field_type[1] in self.classes[class_name]['imports']:
                            package_class_name = f'{self.classes[class_name]['imports'][field_type[1]]}.{field_type[1]}'
                            if package_class_name in self.classes and outerMethodName in \
                                    self.classes[package_class_name]['methods']:
                                self.find_method_by_name(package_class_name, outerMethodName)
                                if self.get_fields_name(outerMethodName) in self.classes[package_class_name]['fields']:
                                    field_annotation, field_field_type = \
                                    self.classes[package_class_name]['fields'][self.get_fields_name(outerMethodName)]
                                    self.req_classes[package_class_name]['fields'][
                                        self.get_fields_name(outerMethodName)] = \
                                        (field_annotation, field_field_type)

                                elif self.set_fields_name(outerMethodName) in self.classes[package_class_name][
                                    'fields']:
                                    field_annotation, field_field_type = \
                                    self.classes[package_class_name]['fields'][self.set_fields_name(outerMethodName)]
                                    self.req_classes[package_class_name]['fields'][
                                        self.set_fields_name(outerMethodName)] = \
                                        (field_annotation, field_field_type)

                            elif package_class_name in self.classes and self.get_fields_name(outerMethodName) in \
                                    self.classes[package_class_name]['fields']:
                                field_field_type = \
                                self.classes[package_class_name]['fields'][self.get_fields_name(outerMethodName)][1]
                                lombok_field = True
                            elif package_class_name.replace("Local", "Bean") in self.classes and outerMethodName in \
                                    self.classes[package_class_name.replace("Local", "Bean")]['methods']:
                                field_field_type = package_class_name.replace("Local", "Bean")
                                self.find_method_by_name(field_field_type, outerMethodName)
                            elif package_class_name.replace("Local", "") in self.classes:
                                field_field_type = package_class_name.replace("Local", "")
                                self.find_method_by_name(field_field_type, outerMethodName)

                            if lombok_field and field_field_type is not None:
                                if field_field_type not in self.req_classes:
                                    self.req_classes[field_field_type] = {'methods': {}, 'fields': {}}
                                self.req_classes[field_field_type]['fields'][self.get_fields_name(outerMethodName)] = \
                                    ([], field_field_type)
                    elif self.get_package_class_name(outerClassName) in self.classes[class_name]['fields']:
                        self.find_method_by_name(
                            self.get_implementation_class(
                                self.classes[class_name]['fields'][self.get_package_class_name(outerClassName)][1]),
                            outerMethodName)
                    elif 'this' == outerClassName:
                        self.find_method_by_name(self.get_package_class_name(class_name), outerMethodName)
                    else:
                        self.find_method_by_name(
                            self.get_package_class_name(f'{self.capitalize_first_char(outerClassName)}'),
                            outerMethodName)

            for inSameClassMethod in innerClassMethods:
                if inSameClassMethod not in [method[1] for method in outerClassMethods]:
                    if f'new {inSameClassMethod}' not in line and f'.{inSameClassMethod}' not in line:
                        self.find_method_by_name(self.get_package_class_name(class_name), inSameClassMethod)

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

    def get_implementation_class(self, input_string):
        return input_string.replace("Local", "Bean")

    def capitalize_first_char(self, input_string):
        if not input_string:
            return input_string  # Return the original string if it's empty or None
        return input_string[0].upper() + input_string[1:]

    def decapitalize_first_char(self, input_string):
        if not input_string:
            return input_string  # Return the original string if it's empty or None
        return input_string[0].lower() + input_string[1:]

    def print_method_body(self, method_body):
        for line in method_body:
            sys.stdout.write(line)

    def get_package_class_name(self, class_name):
        if class_name not in self.classes_package:
            return class_name
        return f'{self.classes_package[class_name][0]}.{class_name}'

    def find_method_by_name_without_package_prefix(self, class_name, method_name):
        package_class_name = f'{self.classes_package[class_name][0]}.{class_name}'
        self.find_method_by_name(package_class_name, method_name)

    def find_method_by_name(self, package_class_name, method_name):
        # if 'getTotalTestTime' == method_name:
        #     print(f'// Class {package_class_name} has method {method_name}')

        if package_class_name in self.req_classes and method_name in self.req_classes[package_class_name]['methods']:
            return
        if package_class_name in self.classes:
            if method_name in self.classes[package_class_name]['methods']:
                for access_modifier, return_type, name, params, body in (
                        self.classes)[package_class_name]['methods'][method_name]:
                    # if 'holdTraveller' == method_name:
                    #     print(f'// Class {class_name} has method {method_name}')
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

                    if package_class_name in self.req_classes:
                        if method_name in self.req_classes[package_class_name]['methods']:
                            self.req_classes[package_class_name]['methods'][method_name].append(
                                (method_and_params, method_content))
                        else:
                            self.req_classes[package_class_name]['methods'][method_name] = [
                                (method_and_params, method_content)]
                    else:
                        self.req_classes[package_class_name] = {'methods': {}, 'fields': {}}
                        self.req_classes[package_class_name]['methods'][method_name] = [
                            (method_and_params, method_content)]

                    # if self.log_flag:
                    #     print(f"{class_name} class has {method_name} method:")
                    #     print(f"{method_content}")
                    self.extract_classes_and_methods(package_class_name, method_name,
                                                     body)  # Call the method to extract classes and methods
                    # return method_content
            elif self.log_flag and method_name not in self.ignored_methods:
                # if 'SimpleQueryBuilder' in method_name:
                #     print(f"// {method_name} method not found")

                not_found_method = f"{package_class_name}.{method_name} not found"
                if not_found_method not in self.not_found_messages:
                    self.not_found_messages.append(not_found_method)
                    print(not_found_method)
        elif self.log_flag and method_name not in self.ignored_methods:
            not_found_class = f"    {package_class_name}.{method_name} not found"
            if not_found_class not in self.not_found_messages:
                self.not_found_messages.append(not_found_class)
                print(not_found_class)

    def generate_java_code(self):
        java_code = ""
        for class_name, class_info in self.req_classes.items():
            java_code += f"class {class_name} {{\n"

            # Add fields to the Java class
            for field_name, (annotation, field_type) in class_info['fields'].items():
                if annotation:
                    annotation_code = ''.join(annotation)
                    java_code += f"{annotation_code}    {field_type} {field_name};\n\n"

            # Add methods to the Java class
            for method_name, methods in class_info['methods'].items():
                for method_and_params, method_content in methods:
                    java_code += f"    {method_content}"

            java_code += "}\n"
        return java_code

    def get_classes_and_methods_content(self):
        java_code = self.generate_java_code()
        self.req_classes = {}
        return java_code

    def get_class_content_by_name(self, class_name):
        return self.classes[class_name]['content']

    def find_class_by_name(self, class_name):
        for method in self.classes[class_name]['methods']:
            self.find_method_by_name(class_name, method)

    def get_fields_name(self, method_name):
        if method_name.startswith("get"):
            return self.decapitalize_first_char(method_name[3:])
        return None

    def set_fields_name(self, method_name):
        if method_name.startswith("set"):
            return self.decapitalize_first_char(method_name[3:])
        return None

    def save_to_file(self, filename):
        try:
            if not os.path.exists(filename) and self.files_to_check is None:
                with open(filename, 'wb') as file:
                    data = {
                        'classes': self.classes,
                        'classes_package': self.classes_package
                    }
                    pickle.dump(data, file)
                print(f"Data saved to {filename}")
            else:
                print(f"File {filename} already exists.")
        except FileExistsError:
            print(f"File {filename} already exists.")

    def load_from_file(self, filename):
        if not os.path.exists(filename):
            print(f"File {filename} does not exist. Cannot load data.")
            return
        with open(filename, 'rb') as file:
            data = pickle.load(file)
            self.classes = data.get('classes', {})
            self.classes_package = data.get('classes_package', {})
        print(f"Data loaded from {filename}")


if __name__ == "__main__":
    parser = JavaParser()
    # parser.parse_file('C:/Users/duc.dangtrong/source/ASE/SpringBoot/testermatrix/src/main/java/com/asesg/aims/testermatrix/web/product/view/AddUpdateASProductAction.java')
    # parser.parse_directory('C:/Users/duc.dangtrong/source/ASE/SpringBoot/testermatrix/src/main/java')
    parser.parse_directory('C:/Users/duc.dangtrong/source/Java/food-ordering-system')

    # parser.print_parsed_methods()
    class_name = 'OrderController'  # input("Enter the class name: ")
    method_name = 'createOrder'  # input("Enter the method name: ")

    # Find method_name in class_name and print it's method body to screen
    parser.find_method_by_name(class_name, method_name)
