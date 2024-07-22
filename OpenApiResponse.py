import re

class OpenApiResponse:
    def __init__(self, java_code):
        self.java_code = java_code

    def extract_method_annotations(self):
        method_pattern = re.compile(r'(@\w+\s*)*')  # Matches annotations
        method_name_pattern = re.compile(r'\b\w+\s*\(')  # Matches method name
        annotations = method_pattern.search(self.java_code).group(0).strip()
        method_name = method_name_pattern.search(self.java_code).group(0).strip()[:-1]  # Remove '(' from method name
        return annotations, method_name

if __name__ == '__main__':
    # Example usage:
    java_code = """
    @Transactional
    @Modifying
    @Query("UPDATE ProgramResource pr SET pr.programResourceStatusId = :statusId WHERE pr.programResourceId = :resourceId")
    int updateProgramResourceStatusById(Long resourceId, String statusId);
    """

    response = OpenApiResponse(java_code)
    annotations, method_name = response.extract_method_annotations()
    print("Method Name:", method_name)
    print("Annotations:", annotations)