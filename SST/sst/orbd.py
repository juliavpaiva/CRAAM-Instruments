import struct
from pathlib import Path
import xml.etree.ElementTree as xmlet
import numpy as np
from astropy.io import fits
from .utils import time

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

    def get_time_span(self):
        nonzero = self.data["time"].nonzero()
        return time.iso_time(self.data["time"][nonzero[0][0]], self.data["time"][nonzero[0][-1]])

    def to_fits(self, name=None, output_path=None):
        t_start, t_end = self.get_time_span()
        if not name:
            name = "sst_{}_{}T{}-{}_level0.fits".format(self.type.lower(), self.date, t_start, t_end)
        
        hdu = fits.PrimaryHDU()
        hdu.header.append(('origin', 'CRAAM/Universidade Presbiteriana Mackenzie', ''))
        hdu.header.append(('telescop', 'Solar Submillimeter Telescope', ''))
        hdu.header.append(('observat', 'CASLEO', ''))
        hdu.header.append(('station', 'Lat = -31.79897222, Lon = -69.29669444, Height = 2.491 km', ''))
        hdu.header.append(('tz', 'GMT-3', ''))

        hdu.header.append(('date-obs', self.date, ''))
        hdu.header.append(('t_start', self.date + 'T' + t_end,''))
        hdu.header.append(('t_end', self.date + 'T' + t_start, ''))
        hdu.header.append(('data_typ', self.type, ''))
        if isinstance(self.filename,list) :
            for name in self.filename:hdu.header.append(('origfile', name, 'SST Raw Binary Data file'))
        else:
            hdu.header.append(('origfile',self.filename, 'SST Raw Binary Data file'))
            
        hdu.header.append(('frequen', '212 GHz ch=1,2,3,4; 405 GHz ch=5,6', ''))

        # About the Copyright
        hdu.header.append(('comment', 'COPYRIGHT. Grant of use.', ''))
        hdu.header.append(('comment', 'These data are property of Universidade Presbiteriana Mackenzie.'))
        hdu.header.append(('comment', 'The Centro de Radio Astronomia e Astrofisica Mackenzie is reponsible'))
        hdu.header.append(('comment', 'for their distribution. Grant of use permission is given for Academic ')) 
        hdu.header.append(('comment', 'purposes only.'))

        #History
        # ...

        dscal = 1.0
        fits_cols = list()
        for child in self.__header:

            var_name = child[0].text
            var_dim = child[1].text
            var_type = child[2].text
            var_unit = child[3].text

            offset = 0
            if var_type == "xs:int":
                var_dim += "J"
                np_type = np.dtype("i4")
            elif var_type == "xs:unsignedShort":
                var_dim += "I"
                np_type = np.dtype("u2")
                offset = 32768
            elif var_type == "xs:short":
                var_dim += "I"
                np_type = np.dtype("i2")
            elif var_type == "xs:byte":
                var_dim += "B"
                np_type = np.dtype("b")
            elif var_type == "xs:float":
                var_dim += "E"
                np_type = np.dtype("f4")
            
            fits_cols.append(fits.Column(name=var_name,
                                         format=var_dim,
                                         unit=var_unit,
                                         bscale=dscal,
                                         bzero=offset,
                                         array=self.data[var_name]))
        
        tbhdu = fits.BinTableHDU.from_columns(fits.ColDefs(fits_cols))
        
        tbhdu.header.append(('comment','Time is in hundred of microseconds (Hus) since 0 UT',''))
        tbhdu.header.append(('comment','ADCu = Analog to Digital Conversion units. Proportional to Voltage',''))
        tbhdu.header.append(('comment','mDeg = milli degree',''))
        tbhdu.header.append(('comment','Temperatures are in Celsius',''))

        hdulist = fits.HDUList([hdu, tbhdu])

        hdulist.writeto(name)


    def __find_xml_header(self, path_to_xml):
        span_table = xmlet.parse(path_to_xml / Path("SSTDataFormatTimeSpanTable.xml")).getroot()
        filetype = "Data" if self.type == "Integration" or self.type == "Subintegration" else "Auxiliary"

        for child in span_table:
            if child[0].text == filetype and child[1].text <= self.date and child[2].text >= self.date:
                data_description_filename = child[3].text
        
        return xmlet.parse(path_to_xml / Path(data_description_filename)).getroot()
        
    def __define_fmt(self):
        bin_header = dict()
        struct_fmt = "="
        for child in self.__header:
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
        
        self.__header = self.__find_xml_header(path_to_xml)
        bin_header, struct_fmt = self.__define_fmt()

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