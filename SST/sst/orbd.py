import struct
from pathlib import Path
import xml.etree.ElementTree as xmlet
import numpy as np

def open_(name, path_to_xml=None):

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

    def __init__(self):
        self.filename = ""
        self.type = ""
        self.date = ""
        self.time = ""
        self.data = dict()

    def __find_xml_header(self, path_to_xml):
        span_table = xmlet.parse(path_to_xml / Path("SSTDataFormatTimeSpanTable.xml")).getroot()
        filetype = "Data" if self.type == "Integration" or self.type == "Subintegration" else "Auxiliary"

        for child in span_table:
            if child[0].text == filetype and child[1].text <= self.date and child[2].text >= self.date:
                data_description_filename = child[3].text
        
        return xmlet.parse(path_to_xml / Path(data_description_filename)).getroot()
        
    def __define_fmt(self, header):
        bin_header = dict()
        struct_fmt = "="

        for child in header:
            var_name = child[0].text
            var_dim = int(child[1].text)
            var_type = child[2].text

            if var_type == "xs:int":
                fmt = "i"
                np_type = np.int32
            elif var_type == "xs:unsignedShort":
                fmt = "H"
                np_type = np.uint16
            elif var_type == "xs:short":
                fmt = "h"
                np_type = np.int16
            elif var_type == "xs:byte":
                fmt = "B"
                np_type = np.byte
            elif var_type == "xs:float":
                fmt = "f"
                np_type = np.float32

            struct_fmt += fmt * var_dim
            bin_header.update({var_name:[var_dim, np_type]})
            
        return bin_header, struct_fmt

    def from_file(self, path, path_to_xml):

        self.filename = path.name
        type_prefix = self.filename[:2].upper()

        if type_prefix == "RS":
            self.type = "Integration"
        elif type_prefix == "RF":
            self.type = "Subintegration"
        elif type_prefix == "BI":
            self.type = "Auxiliary"
        else:
            #raise exception invalid filename
            pass

        date = self.filename[2:].split(".")

        """
        date[0] = date[0][::-1]
        day = date[0][:2][::-1]
        month = date[0][2:4][::-1]
        year = int(date[0][4:][::-1]) + 1900
        self.date = "{}-{}-{}".format(year,month,day)
        """

        if len(date[0]) == 6:
            self.date = str(int(date[0][:2]) + 1900) + '-' + date[0][2:4] + '-' + date[0][4:6]
        elif len(date[0]) == 7:
            self.date = str(int(date[0][:3]) + 1900) + '-' + date[0][3:5] + '-' + date[0][5:7]
        else:
            #raise exception invalid filename
            pass

        self.time = "00:00"
        if len(date) > 1:
            self.time = date[1][:2] + ":" + date[1][2:4]
        
        header = self.__find_xml_header(path_to_xml)
        bin_header, struct_fmt = self.__define_fmt(header)

        with open(path, "rb") as f:
            
            f.seek(0,2)
            fsize = f.tell()
            f.seek(0)

            struct_size = struct.calcsize(struct_fmt)
            nrecords = fsize // struct_size

            for name, dim in bin_header.items():
                if dim[0] > 1:
                    self.data.update({name:np.array(np.empty([nrecords, dim[0]], dim[1]))})
                else:
                    self.data.update({name:np.array(np.empty([nrecords], dim[1]))})

            data_pos = 0
            buffer = f.read(struct_size)
            while buffer != b'':
                raw_data = struct.unpack(struct_fmt, buffer)
                
                bin_pos = 0
                for name, dim in bin_header.items():
                    if dim[0] == 1:
                        self.data[name][data_pos] = raw_data[bin_pos]
                    else:
                        self.data[name][data_pos] = raw_data[bin_pos:bin_pos+dim[0]]
                    bin_pos += dim[0]

                buffer = f.read(struct_size)
                data_pos += 1

        return self