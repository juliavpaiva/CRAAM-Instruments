from pathlib import Path

def open(name, path_to_xml=None):

    name = Path(name).expanduser()

    """
        If the xml path was not defined it assumes the path is XMLtables
        inside the module's own directory. __file__ is a python variable
        that stores where the module is located.
    """

    if not path_to_xml:
        path_to_xml = Path(__file__).parent / Path("XMLtables/")
    else:
        path_to_xml = Path(path_to_xml)

    if not name.exists():
        raise FileNotFoundError("File not found: {}".format(name))

    if not path_to_xml.is_dir():
        raise ValueError("Invalid path to XML: {}".format(path_to_xml))

    return RBD().from_file(name, path_to_xml)
    

class RBD:

    def from_file(self, name, path_to_xml):

        """
        from_file
           It is the class method used to read a SST Raw Binary Data (RBD) from a file. The 
           data is represented with class attributes representing SST variables, and data
           is stored in a numpy ndarray. Every ndarray has the python dtype corresponding
           to the original SST data. 

        Output:
           It returns a RBD object

        Change Record:
           First Written by Guigue @ Sampa - 2017-08-26

        """

        return self