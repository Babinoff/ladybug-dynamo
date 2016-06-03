import epw
import skyvector
from .dt import LBDateTime
from .analysisperiod import AnalysisPeriod
from .datacollection import LBDataCollection
from .header import Header
from .datatype import LBData, SkyPatch
import os
import subprocess
from time import sleep

class CumulativeSkyMtx(object):
    """Cumulative Sky.

    Attributes:
        epwFileAddress: Path to EPW file.
        skyDensity: Density of the sky. 0 generates a Tregenza sky, which will
            divide up the sky dome with a coarse density of 145 sky patches.
            Set to 1 to generate a Reinhart sky, which will divide up the sky dome
            using a density of 580 sky patches.
        workingDir: A local directory to run the study and write the results

    Usage:

        epwfile = r"C:/EnergyPlusV8-3-0/WeatherData/USA_CO_Golden-NREL.724666_TMY3.epw"
        cumSky = CumulativeSkyMtx(epwfile) #calculate the sky
        # annual results
        cumSky.annualResults()

        # results for an anlysis period
        ap = AnalysisPeriod(startMonth = 2, endMonth = 12)
        results = cumSky.filterByAnalysisPeriod(ap)
        print results.diffuseValues
    """
    _rowNumber = (
        (0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
         1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
         2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3,
         3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4,
         4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5,
         5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
         6, 7, 7, 7, 7, 7, 7, 8),
        (0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
         1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
         1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2,
         2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
         2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
         2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
         3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
         3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4,
         4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
         4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
         4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
         5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
         5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
         6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
         6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7,
         7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
         7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 8, 8, 8, 8, 8, 8,
         8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
         8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9,
         9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9,
         9, 9, 9, 9, 9, 9, 9, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
         10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
         10, 10, 10, 10, 10, 10, 10, 10, 10, 11, 11, 11, 11, 11, 11, 11, 11,
         11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 12,
         12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12,
         12, 12, 12, 12, 12, 12, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13,
         13, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 15)
    )

    def __init__(self, epwFileAddress, skyDensity=0, workingDir=None):
        """Init class."""
        self.__epw = epw.EPW(epwFileAddress)
        self.__data = {"diffuse": None, "direct": None}
        self.__results = {}
        self.skyDensity = skyDensity
        self.__isCalculated = False
        self.__isLoaded = False
        self.workingDir = workingDir

    @property
    def rawdata(self):
        """Get raw data a dictionary."""
        return self.__data

    @property
    def skyDensity(self):
        """Return sky density.

        0: Tregenza, 1: Reinhart
        """
        return self.__skyDensity

    @skyDensity.setter
    def skyDensity(self, density):
        assert int(density) <= 1, \
            "Sky density is should be 0: Tregenza sky, 1: Reinhart sky"
        self.__skyDensity = int(density)
        self.__data = {"diffuse": None, "direct": None}

    @property
    def workingDir(self):
        """A local directory to run the study and write the results."""
        return self.__workingDir

    @workingDir.setter
    def workingDir(self, workingDir):
        # update addresses
        self.__workingDir = workingDir

        if not self.__workingDir:
            self.__workingDir = self.__epw.filePath

        # add name of city to path
        if not self.__workingDir.endswith(self.__epw.location.city):
            self.__workingDir = os.path.join(self.__workingDir,
                                             self.__epw.location.city.replace(" ", "_"))

        # create the folder is it's not created
        if not os.path.isdir(self.__workingDir):
            os.mkdir(self.__workingDir)

        # update path for other files if it's a new workingDir
        # naming convention is weatherFileName_[diffuse/direct]_[skyDensity].mtx
        __name = self.__epw.fileName[:-4] + "_%s_%d.mtx"

        self.__diffuseMtxFileAddress = os.path.join(
            self.__workingDir, __name % ("dif", self.__skyDensity)
        )

        self.__directMtxFileAddress = os.path.join(
            self.__workingDir, __name % ("dir", self.__skyDensity)
        )

        self.__jsonFileAddress = os.path.join(
            self.__workingDir,
            self.__epw.fileName[:-4] + "_" + str(self.__skyDensity) + ".json"
        )

    @property
    def numberOfPatches(self):
        """Return number of patches."""
        return self.__patchData("numberOfPatches")

    @property
    def skyDiffuseRadiation(self):
        """Diffuse values for sky patches as a LBDataList."""
        assert self.__isCalculated, "You need to calculate the materix first before" + \
            " loading the results. Use calculateMtx method.\nIf you see this error from inside " + \
            "Dynamo reconnect one of the inputs and re-run the file!\nFiles are created under %s" % self.workingDir

        assert self.__isLoaded, "The values are not loaded. Use skyMtx method."

        return self.__results["diffuse"]

    @property
    def skyDirectRadiation(self):
        """Direct values for sky patches as a LBDataList."""
        assert self.__isCalculated, "You need to calculate the materix first before" + \
            " loading the results. Use calculateMtx method.\nIf you see this error from inside " + \
            "Dynamo reconnect one of the inputs and re-run the file!\nFiles are created under %s" % self.workingDir

        assert self.__isLoaded, "The values are not loaded. Use skyMtx method."

        return self.__results["direct"]

    @property
    def skyTotalRadiation(self):
        """Total values for sky patches as a LBDataList."""
        assert self.__isCalculated, "You need to calculate the materix first before" + \
            " loading the results. Use calculateMtx method.\nIf you see this error from inside " + \
            "Dynamo reconnect one of the inputs and re-run the file!\nFiles are created under %s" % self.workingDir

        assert self.__isLoaded, "The values are not loaded. Use skyMtx method."

        return self.__results["total"]
        # return tuple(diff + dirr for diff, dirr
        #              in zip(self.skyDiffuseRadiation, self.skyDirectRadiation))

    def steradianConversionFactor(self, patchNumber):
        """Steradian Conversion Factor."""
        rowNumber = self.__calculateRowNumber(patchNumber)
        strConv = self.__patchData("steradianConversionFactor")[rowNumber]
        return strConv

    def __patchData(self, key):
        """
        Return data for sky patches based on key.

        Args:
            key: valid keys are numberOfPatches, numberOfPatchesInEachRow and steradianConversionFactor.

        Return:
            Data for this sky based on the sky density. Depending on the key it can be a number or a list of numbers

        Usage:

            self.__patchesData(0)
            >> 146
        """
        # first row is horizon and last row is values for the zenith
        # first patch is the ground. I put 0 on conversion
        __data = {
            "numberOfPatches": {0: 146, 1: 578},

            "numOfPatchesInEachRow": {
                0: [1, 30, 30, 24, 24, 18, 12, 6, 1],
                1: [1, 60, 60, 60, 60, 48, 48, 48, 48, 36, 36, 24, 24, 12, 12, 1]
            },

            "steradianConversionFactor": {

                0: [0, 0.0435449227, 0.0416418006, 0.0473984151,
                    0.0406730411, 0.0428934136, 0.0445221864, 0.0455168385, 0.0344199465],

                1: [0, 0.0113221971, 0.0111894547, 0.0109255262, 0.0105335058, 0.0125224872,
                    0.0117312774, 0.0108025291, 0.00974713106, 0.011436609, 0.00974295956,
                    0.0119026242, 0.00905126163, 0.0121875626, 0.00612971396, 0.00921483254]
            }
        }

        try:
            return __data[key][self.__skyDensity]
        except KeyError:
            raise KeyError("Invalid key: %s." % key)

    def __calculateRowNumber(self, patchNumber):
        """Calculate number of row for sky patch."""
        return self._rowNumber[self.skyDensity][patchNumber]

    def epw2wea(self, filePath=None):
        """Convert epw file to wea file.

        filePath: Optional filepath to an epw file. If not self.__epw will be
            used.
        """
        if not filePath:
            filePath = os.path.join(self.__workingDir, self.__epw.fileName[:-4] + ".wea")

        self.__weaFileAddress = self.__epw.epw2wea(filePath)

    def calculateMtx(self, pathToRadianceBinaries=r"c:\radiance\bin",
                     recalculate=False):
        """use Radiance gendaymtx to generate the sky.

        Args:
            pathToRadianceBinaries: Path to Radiance libraries. Default is
                C:/radiance/bin.
            recalculate: Set to True if you want the sky to be recalculated
                even it has been calculated already
        """
        # check if the result is already calculated
        if not recalculate:
            if os.path.isfile(self.__diffuseMtxFileAddress) and \
                    os.path.isfile(self.__directMtxFileAddress):
                self.__isCalculated = True
                return

        if not pathToRadianceBinaries:
            pathToRadianceBinaries = r"c:\radiance\bin"

        assert os.path.isfile(os.path.join(pathToRadianceBinaries, "gendaymtx.exe")) \
            and os.path.isfile(os.path.join(pathToRadianceBinaries, "rcollate.exe")), \
            "Can't find gendaymtx.exe or rcollate.exe in radiance binary folder."

        # make sure daymtx and rcollate can be executed
        gendaymtxPath = os.path.join(pathToRadianceBinaries, "gendaymtx.exe")
        assert os.access(gendaymtxPath, os.X_OK), \
            "%s is blocked by system! Right click on the file," % gendaymtxPath + \
            " select properties and unblock it."

        rcollatePath = os.path.join(pathToRadianceBinaries, "rcollate.exe")
        assert os.access(rcollatePath, os.X_OK), \
            "%s is blocked by system! Right click on the file," % rcollatePath + \
            " select properties and unblock it."

        # assure wea file is calculated
        if not hasattr(self, "__weaFileAddress"):
            self.epw2wea()

        __name = self.__epw.fileName[:-4] + "_calculate_sky_mtx.bat"
        batchFileAddress = os.path.join(self.__workingDir, __name)

        batchFile = "@echo off\n" \
            "echo.\n" \
            "echo HELLO! DO NOT CLOSE THIS WINDOW.\n" \
            "echo IT WILL BE CLOSED AUTOMATICALLY WHEN THE CALCULATION IS OVER!\n" \
            "echo.\n" \
            "echo.\n" \
            "echo AND MAY TAKE FEW MINUTES...\n" \
            "echo.\n" \
            "PATH={6};\n" \
            "echo CALCULATING DIFFUSE COMPONENT OF THE SKY...\n" \
            "{0} -m {2} -s -O1 {3} > {4}\n" \
            "echo.\n" \
            "echo CALCULATING DIRECT COMPONENT OF THE SKY...\n" \
            "{0} -m {2} -d -O1 {3} > {5}\n".format(
                "gendaymtx",
                "rcollate",
                self.skyDensity + 1,
                self._normspace(self.__weaFileAddress),
                self._normspace(self.__diffuseMtxFileAddress),
                self._normspace(self.__directMtxFileAddress),
                self._normspace(pathToRadianceBinaries)
            )

        # write batch file
        with open(batchFileAddress, "wb") as genskymtxbatfile:
            genskymtxbatfile.write(batchFile)

        # p = subprocess.Popen(batchFileAddress, shell=True,
        #                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        #
        # for line in p.stdout.readlines():
        #     print line,
        # p.wait()

        os.system(self._normspace(batchFileAddress))
        sleep(1)
        if os.path.isfile(self.__directMtxFileAddress):
            self.__isCalculated = True

    def _normspace(self, path):
        """Norm filepath with white space."""
        return path if path.find(" ") == -1 else '"%s"' % path

    def __calculateLuminanceFromRGB(self, patchNumber, *args):
        try:
            r, g, b = (float(i) for i in args)
        except ValueError:
            # empty line
            return "Empty Line"

        return (.265074126 * r +
                .670114631 * g +
                .064811243 * b) * self.steradianConversionFactor(patchNumber)

    def __readMtxFile(self, f):
        # results is a tuple with the length of number of patches.
        # each item in the list is a tuple with 8760 values for each hour
        with open(f, 'rb') as inf:
            for i in xrange(8):
                inf.readline()
            return tuple(tuple((self.__calculateLuminanceFromRGB(i, *inf.readline().split(" "))
                                for j in range(8761)))
                         for i in xrange(self.numberOfPatches))

    def __loadMtxFiles(self):
        """load the values from .mtx files.

        use self.skyMtx to get the results
        """
        if self.__isLoaded:
            print "Matrix has been already loaded!"
            return

        assert self.__isCalculated, "You need to calculate the materix first before" + \
            " loading the results. Use calculateMtx method. If you see this error from inside " + \
            "Dynamo reconnect one of the inputs and re-run the file!"

        assert os.path.getsize(self.__diffuseMtxFileAddress) > 0 and \
            os.path.getsize(self.__directMtxFileAddress) > 0, \
            "Size of matrix files is 0. Try to recalculate cumulative sky matrix."

        # open files and read the lines
        self.__data["diffuse"] = self.__readMtxFile(self.__diffuseMtxFileAddress)
        self.__data["direct"] = self.__readMtxFile(self.__directMtxFileAddress)

        self.__isLoaded = True

    # TODO: Analysis periods in headers should be adjusted based on the input
    def gendaymtx(self, pathToRadianceBinaries=None, diffuse=True, direct=True,
                  recalculate=False, analysisPeriod=None):
        """Get sky matrix for direct, diffuse and total radiation as three separate lists.

        Args:
            pathToRadianceBinaries: Path to Radiance libraries. Default is
                C:/radiance/bin.
            diffuse: Set to True to include diffuse radiation
            direct: Set to True to iclude direct radiation
            recalculate: Set to True if you want the sky to be recalculated even
                it has been calculated already.
            analysisPeriod: An analysis period or a list of integers between
                0-8759 for hours of the year. Default is All the hours of the
                year.
        """
        # calculate sky if it's not already calculated
        if not self.__isCalculated or recalculate:
            self.calculateMtx(pathToRadianceBinaries=pathToRadianceBinaries,
                              recalculate=recalculate)

        # load matrix files if it's not loaded
        if not self.__isLoaded:
            self.__loadMtxFiles()

        if not analysisPeriod:
            HOYs = range(8760)
        else:
            if isinstance(analysisPeriod, list):
                HOYs = tuple(int(h) if -1 < h < 8760 else -1 for h in analysisPeriod)
                assert (-1 not in HOYs), "Hour should be between 0-8759"

            elif isinstance(analysisPeriod, AnalysisPeriod):
                HOYs = analysisPeriod.HOYs
            else:
                raise ValueError(
                    "Analysis period should be a list of integers or an analysis period."
                )

        # calculate values and return them as 3 lists
        # put 0 value for all the patches
        __cumulativeRaditionValues = {
            "diffuse": [0] * self.numberOfPatches,
            "direct": [0] * self.numberOfPatches
        }

        for patchNumber in range(self.numberOfPatches):
            for HOY in HOYs:
                __cumulativeRaditionValues["diffuse"][patchNumber] += self.__data["diffuse"][patchNumber][HOY]
                __cumulativeRaditionValues["direct"][patchNumber] += self.__data["direct"][patchNumber][HOY]

        # create header for each patch
        difHeader = Header(location=self.__epw.location,
                           analysisPeriod=None,
                           dataType="Sky Patches' Diffues Radiation",
                           unit="Wh")

        dirHeader = Header(location=self.__epw.location,
                           analysisPeriod=None,
                           dataType="Sky Patches' Direct Radiation",
                           unit="Wh")

        totalHeader = Header(location=self.__epw.location,
                             analysisPeriod=None,
                             dataType="Sky Patches' Total Radiation",
                             unit="Wh")

        # create an empty data list with the header
        __skyVectors = skyvector.Skyvectors(self.__skyDensity)

        self.__results = {}

        self.__results['diffuse'] = LBDataCollection(header=difHeader)
        self.__results['direct'] = LBDataCollection(header=dirHeader)
        self.__results['total'] = LBDataCollection(header=totalHeader)

        for patchNumber in range(self.numberOfPatches):

            __diff = __cumulativeRaditionValues["diffuse"][patchNumber] \
                if diffuse else 0

            __dir = __cumulativeRaditionValues["direct"][patchNumber] \
                if direct else 0

            self.__results['diffuse'].append(SkyPatch(__diff,
                                                      __skyVectors[patchNumber]))

            self.__results['direct'].append(SkyPatch(__dir,
                                                     __skyVectors[patchNumber]))

            self.__results['total'].append(SkyPatch(__diff + __dir,
                                                    __skyVectors[patchNumber]))

        del(__cumulativeRaditionValues)

    def toJson(self):
        """Convert sky matrix files to json object."""
        raise NotImplementedError

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        """Sky matrix representation."""
        return "Ladybug.SkyMatrix > %s" % self.__epw.location.city
