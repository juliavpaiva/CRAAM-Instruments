from pathlib import Path
import xml.etree.ElementTree as xmlet
import numpy as np
from astropy.io import fits
from .utils import time

def open(path, name=None, path_to_xml=None):
    """Function to open a RBD file and return an `RBD` object.

    Parameters
    ----------
    path : str, pathlib.Path, buffer
        File to be opened.

    name : str, optional
        Name of the RBD file. Only needed if path
        is a buffer.

    path_to_xml : str, pathlib.Path, optional
        Location of the RBD xml description files in the file system.
        If not defined it is assumed that the path is XMLtables
        within the module's own directory.
    
    Raises
    ------
    FileNotFoundError
        If the RBD file was not found.
    
    ValueError
        If the path to the xml files is invalid.
    """

    if not path_to_xml:
        # __file__ is a python variable that stores where the module is located.
        path_to_xml = Path(__file__).parent / Path("XMLtables/")
    else:
        path_to_xml = Path(path_to_xml)

    if not isinstance(path, bytes):
        path = Path(path).expanduser()
        if not path.exists():
            raise FileNotFoundError("File not found: {}".format(path))
        name = path.name
        
    if not path_to_xml.exists():
        raise ValueError("Invalid path to XML: {}".format(path_to_xml))

    return RBD().from_file(path, name, path_to_xml)
    
def concatenate(rbds):
        """
        Method for concatenating RBDs. It returns a new RBD object
        representing the concatenated data ordered by time.

        Parameters
        ----------
            rbds : list, tuple
                List or tuple of RBD objects to be concatenated.
                The objects must have the same data structure.
        
        Raises
        ------
        TypeError
            If the objects have different data structures.
        """

        try:
            new_data = np.concatenate([rbd.data for rbd in rbds])
        except TypeError:
            raise TypeError("The objects must have the same data structures.")
        
        #Order the data by time
        new_data = new_data[new_data["time"].argsort()]

        rbd = RBD()

        filenames = list()
        for r in rbds:
            if isinstance(r.filename, list):
                filenames.extend(r.filename)
            else:
                filenames.append(r.filename)

        filenames = sorted(filenames)

        rbd.filename = filenames

        rbd.type = rbds[0].type
        rbd.date = rbds[0].date
        rbd.data = new_data
        
        date = filenames[0].split(".")
        time = "00:00"
        if len(date) > 1:
            time = date[1][:2] + ":" + date[1][2:4]

        rbd.time = time

        rbd._header = rbds[0]._header
        rbd.history.append("Concatenated Data")

        return rbd

class RBD:

    def __init__(self):
        self.filename = ""
        self.type = ""
        self.date = ""
        self.time = ""
        self.data = np.empty((0))
        self.history = list()

    def __add__(self, other):
        """
        Magic method for concatenating RBDs.
        Usage: rbd3 = rbd1 + rbd2
        """
        
        return concatenate((self, other))

    @property
    def columns(self):
        """Returns the names of the columns in a tuple."""

        return self.data.dtype.names

    def reduced(self, columns=None):
        """Returns a reduced version of the RBD

        By default the reduced version contains:
             
             time    : time in Hus
             azipos  : encoder's azimuth
             elepos  : encoder's elevation
             adc or adcval : receiver's output
             opmode  : oberving mode
             target  : target observed
             x_off   : scan offset in azimuth
             y_off   : scan offset in elevation

        Parameters
        ----------
        columns : list, optional
            List of which columns the reduced version should contain.
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
        rbd._header = {column:self._header[column] for column in columns}
        rbd.data = self.data[[name for name in columns]]

        rbd.history.append("Reduced Data File. Selected Variables saved")

        return rbd

    def get_time_span(self):
        """
        Returns a tuple containing the ISO time of the
        first and last record found in the data.
        """

        nonzero = self.data["time"].nonzero()
        return (time.iso_time(self.data["time"][nonzero[0][0]]), time.iso_time(self.data["time"][nonzero[0][-1]]))

    def to_fits(self, name=None, output_path=None):
        """Writes the RBD data to a FITS file.

        By default the name of the fits file is defined as:

        sst_[integration | subintegration | auxiliary]_YYYY-MM-DDTHH:MM:SS.SSS-HH:MM:SS.SSS_level0.fits

        The file has two HDUs. The primary containing just a header with general
        information such as the origin, telescope, time zone. The second is a BinaryTable
        containing the data and a header with data specific information.

        Parameters
        ----------
        name : str, optional
            Name of the fits file.
        
        output_path : str, pathlib.Path, optional
            Output path of the fits file. By default
            is where the script is being called from.
        
        Raises
        ------
        FileExistsError
            If a file with the same name already exists
            in the output path.
        """

        t_start, t_end = self.get_time_span()

        if not name:
            name = "sst_{}_{}T{}-{}_level0.fits".format(self.type.lower(), self.date, t_start, t_end)
        else:
            if not name.endswith(".fits"):
                name += ".fits"
        
        name = Path(name)

        if not output_path:
            output_path = "."

        output_path = Path(output_path).expanduser()
        
        if (output_path / name).exists():
            raise FileExistsError("File {} already exists.".format(str(name)))

        hdu = fits.PrimaryHDU()
        hdu.header.append(('origin', 'CRAAM/Universidade Presbiteriana Mackenzie', ''))
        hdu.header.append(('telescop', 'Solar Submillimeter Telescope', ''))
        hdu.header.append(('observat', 'CASLEO', ''))
        hdu.header.append(('station', 'Lat = -31.79897222, Lon = -69.29669444, Height = 2.491 km', ''))
        hdu.header.append(('tz', 'GMT-3', ''))

        hdu.header.append(('date-obs', self.date, ''))
        hdu.header.append(('t_start', self.date + 'T' + t_start,''))
        hdu.header.append(('t_end', self.date + 'T' + t_end, ''))
        hdu.header.append(('data_typ', self.type, ''))
        if isinstance(self.filename, list) :
            for fname in self.filename: hdu.header.append(('origfile', fname, 'SST Raw Binary Data file'))
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
        for column, values in self._header.items():

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
        """
        Method for finding the correct description file.
        Returns a dict representing the description found,
        the key is the variable name and the value is a list
        containing the var dimension, type and unit respectively.
        """

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

    def from_file(self, path, name, path_to_xml):
        """Loads data from a file and returns an `RBD` object.

        Parameters
        ----------
            path : pathlib.Path
                Location of the RBD file in the file system.

            name : str
                Name of the RBD file.

            path_to_xml : Path, optional
                Location of the RBD xml description files in the file system.

        Raises
        ------
        ValueError
            If the filename is invalid.
        """

        self.filename = name
        type_prefix = self.filename[:2].upper()

        if type_prefix == "RS":
            self.type = "Integration"
        elif type_prefix == "RF":
            self.type = "Subintegration"
        elif type_prefix == "BI":
            self.type = "Auxiliary"
        else:
            raise ValueError("Invalid filename {}".format(self.filename))

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
            raise ValueError("Invalid filename {}".format(self.filename))

        self.time = "00:00"
        if len(date) > 1:
            self.time = date[1][:2] + ":" + date[1][2:4]
        
        self._header = self.__find_header(path_to_xml)

        dt_list = list()
        for key, value in self._header.items():
            dt_list.append((key, value[1], value[0]))
        
        if isinstance(path, bytes):
            self.data = np.frombuffer(path, dtype=dt_list)
        else:
            self.data = np.fromfile(str(path), dtype=dt_list)

        return self