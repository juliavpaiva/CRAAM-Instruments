from pathlib import Path
import xml.etree.ElementTree as xmlet
import numpy as np
from astropy.io import fits
from .utils import time

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

    def __init__(self):
        self.filename = ""
        self.type = ""
        self.date = ""
        self.time = ""
        self.data = np.empty((0))
        self.history = list()

    @property
    def columns(self):
        """Returns the names of the columns in a tuple."""
        return self.data.dtype.names

    def reduced(self, columns=None):
        """
        Returns a reduced version of the RBD.
        By default the reduced version contains:
        'time','adc','adcval','elepos','azipos','opmode','target','x_off','y_off'

        It is possible to select which columns the reduced version should have by
        passing a list containing the names of the wanted columns.
        """

        if not columns:
            adc = "adc" if "adc" in self.columns else "adcval"
            columns = ['time', adc,'elepos','azipos',
                        'opmode','target','x_off','y_off']

        rbd = RBD()
        rbd.filename = self.filename
        rbd.type = self.type
        rbd.date = self.date
        rbd.time = self.time
        
        #dict() needed so new_header becomes a copy not a pointer
        new_header = dict(self.__header)

        for column in self.__header.keys():
            if not column in columns:
                new_header.pop(column)
        
        rbd.__header = new_header
        rbd.data = self.data[[name for name in columns]]

        rbd.history.append("Reduced Data File. Selected Variables saved")

        return rbd

    def get_time_span(self):
        nonzero = self.data["time"].nonzero()
        return time.iso_time(self.data["time"][nonzero[0][0]], self.data["time"][nonzero[0][-1]])

    def to_fits(self, name=None, output_path=None):
        t_start, t_end = self.get_time_span()

        if not name:
            name = "sst_{}_{}T{}-{}_level0.fits".format(self.type.lower(), self.date, t_start, t_end)
        name = Path(name)

        if not output_path:
            output_path = "."
        output_path = Path(output_path)
        
        if (output_path / name).exists():
            raise FileExistsError("File {} already exists.".format(str(name)))

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
        hdu.header.append(("history", "Converted to FITS level-0 with orbd.py"))

        for hist in self.history:
            hdu.header.append(("history", hist))

        dscal = 1.0
        fits_cols = list()
        for column, values in self.__header.items():

            var_dim = str(values[0])

            offset = 0
            if values[1] == np.int32:
                var_dim += "J"
            elif values[1] == np.uint16:
                var_dim += "I"
                offset = 32768
            elif values[1] == np.int16:
                var_dim += "I"
            elif values[1] == np.byte:
                var_dim += "B"
            elif values[1] == np.float32:
                var_dim += "E"
            
            fits_cols.append(fits.Column(name=column,
                                         format=var_dim,
                                         unit=values[2],
                                         bscale=dscal,
                                         bzero=offset,
                                         array=self.data[column]))
        
        tbhdu = fits.BinTableHDU.from_columns(fits.ColDefs(fits_cols))
        
        tbhdu.header.append(('comment','Time is in hundred of microseconds (Hus) since 0 UT',''))
        tbhdu.header.append(('comment','ADCu = Analog to Digital Conversion units. Proportional to Voltage',''))
        tbhdu.header.append(('comment','mDeg = milli degree',''))
        tbhdu.header.append(('comment','Temperatures are in Celsius',''))

        hdulist = fits.HDUList([hdu, tbhdu])

        hdulist.writeto(output_path / name)

    def __find_header(self, path_to_xml):
        span_table = xmlet.parse(path_to_xml / Path("SSTDataFormatTimeSpanTable.xml")).getroot()
        filetype = "Data" if self.type == "Integration" or self.type == "Subintegration" else "Auxiliary"

        for child in span_table:
            if child[0].text == filetype and child[1].text <= self.date and child[2].text >= self.date:
                data_description_filename = child[3].text
        
        xml = xmlet.parse(path_to_xml / Path(data_description_filename)).getroot()
        
        header = dict()
        for child in xml:
            var_name = child[0].text
            var_dim = int(child[1].text)
            var_type = child[2].text
            var_unit = child[3].text

            if var_type == "xs:int":
                np_type = np.int32
            elif var_type == "xs:unsignedShort":
                np_type = np.uint16
            elif var_type == "xs:short":
                np_type = np.int16
            elif var_type == "xs:byte":
                np_type = np.byte
            elif var_type == "xs:float":
                np_type = np.float32

            header.update({var_name:[var_dim, np_type, var_unit]})

        return header

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
        
        self.__header = self.__find_header(path_to_xml)

        dt_list = list()
        for key, value in self.__header.items():
            dt_list.append((key, value[1], value[0]))
        
        self.data = np.fromfile(str(path), dtype=dt_list)

        return self