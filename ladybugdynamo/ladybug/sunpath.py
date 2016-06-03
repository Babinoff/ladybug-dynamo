import math
from .location import Location
from .dt import LBDateTime
from .euclid import Vector3


class LBSunpath(object):
    """
    Calculates sun path.

    Attributes:
        latitude: The latitude of the location in degrees. Values must be
            between -90 and 90. Default is set to the equator.
        northAngle: Angle to north (0-360). 90 is west and 270 is east
            (Default: 0)
        longitude: The longitude of the location in degrees (Default: 0)
        timezone: A number representing the time zone of the location you are
            constructing. This can improve the accuracy of the resulting sun
            plot.  The time zone should follow the epw convention and should be
            between -12 and +12, where 0 is at Greenwich, UK, positive values
            are to the East of Greenwich and negative values are to the West.
        daylightSavingPeriod: An analysis period for daylight saving.
            (Default: None)

    Usage:

        import ladybug.sunpath as sunpath
        # initiate sunpath
        sp = sunpath.LBSunpath(50)
        sun = sp.calculateSun(1, 1, 12) # calculate sun data for Jan 1 at noon
        print sun.azimuth, sun.altitude
    """

    __slots__ = ('__longitude', '__latitude', 'northAngle', 'timezone',
                 'daylightSavingPeriod')
    PI = math.pi

    def __init__(self, latitude=0, northAngle=0, longitude=0, timezone=0,
                 daylightSavingPeriod=None):
        """Init sunpath."""
        self.timezone = timezone
        self.latitude = latitude
        self.longitude = longitude
        self.northAngle = northAngle
        self.daylightSavingPeriod = daylightSavingPeriod

    @classmethod
    def fromLocation(cls, location, northAngle=0, daylightSavingPeriod=None):
        """Create a sun path from a LBlocation."""
        location = Location.fromLocation(location)
        return cls(location.latitude, northAngle, location.longitude,
                   location.timezone, daylightSavingPeriod)

    @property
    def latitude(self):
        """Get/set latitude in degrees."""
        return math.degrees(self.__latitude)

    @latitude.setter
    def latitude(self, value):
        """Set latitude value."""
        self.__latitude = math.radians(float(value))
        assert -self.PI / 2 <= self.__latitude <= self.PI / 2, \
            "latitude value should be between -90..90."

    @property
    def longitude(self):
        """Get longitude in degrees."""
        return math.degrees(self.__longitude)

    @longitude.setter
    def longitude(self, value):
        """Set longitude value in degrees."""
        self.__longitude = math.radians(float(value))

        # update timezone
        if abs((value / 15.0) - self.timezone) > 1:
            # if timezone doesn't match the longitude update the timezone
            self.timezone = value / 15.0

    def isDaylightSavingHour(self, datetime):
        """Check if a datetime is a daylight saving time."""
        if not self.daylightSavingPeriod:
            return False
        return self.daylightSavingPeriod.isTimeIncluded(datetime.HOY)

    def calculateSun(self, month, day, hour, isSolarTime=False):
        """Get Sun data for an hour of the year.

        Args:
            month: An integer between 1-12
            day: An integer between 1-31
            hour: A positive number between 0..23
            isSolarTime: A boolean to indicate if the input hour is solar time.
                (Default: False)

        Returns:
            A sun object for this particular time
        """
        datetime = LBDateTime(month, day, *self.__calculateHourAndMinute(hour))
        return self.calculateSunFromDataTime(datetime, isSolarTime)

    def calculateSunFromHOY(self, HOY, isSolarTime=False):
        """Get Sun data for an hour of the year.

        Args:
            datetime: Ladybug datetime
            isSolarTime: A boolean to indicate if the input hour is solar time. (Default: False)

        Returns:
            A sun object for this particular time
        """
        datetime = LBDateTime.fromHOY(HOY)
        return self.calculateSunFromDataTime(datetime, isSolarTime)

    def calculateSunFromDataTime(self, datetime, isSolarTime=False):
        """Get Sun for an hour of the year.

        This code is originally written by Trygve Wastvedt (Trygve.Wastvedt@gmail.com)
        based on (NOAA) and modified by Chris Mackey and Mostapha Roudsari

        Args:
            datetime: Ladybug datetime
            isSolarTime: A boolean to indicate if the input hour is solar time.
                (Default: False)

        Returns:
            A sun object for this particular time
        """
        solDec, eqOfTime = self.__calculateSolarGeometry(datetime)

        hour = datetime.floatHour

        isDaylightSaving = self.isDaylightSavingHour(datetime.HOY)

        hour = hour + 1 if self.isDaylightSavingHour(datetime.HOY) else hour

        # hours
        solTime = self.__calculateSolarTime(hour, eqOfTime, isSolarTime)

        # degrees
        hourAngle = (solTime * 15 + 180) if (solTime * 15 < 0) \
            else (solTime * 15 - 180)

        # RADIANS
        zenith = math.acos(math.sin(self.__latitude) * math.sin(solDec) +
                           math.cos(self.__latitude) * math.cos(solDec) *
                           math.cos(math.radians(hourAngle)))

        altitude = (math.pi / 2) - zenith

        if hourAngle == 0.0 or hourAngle == -180.0 or hourAngle == 180.0:

            azimuth = math.pi if solDec < self.__latitude else 0.0

        else:
            azimuth = (
                (math.acos(
                    (
                        (math.sin(self.__latitude) *
                         math.cos(zenith)) - math.sin(solDec)
                    ) /
                    (
                        math.cos(self.__latitude) * math.sin(zenith)
                    )
                ) + math.pi) % (2 * math.pi)) if (hourAngle > 0) \
                else \
                (
                    (3 * math.pi -
                     math.acos(((math.sin(self.__latitude) * math.cos(zenith)) -
                                math.sin(solDec)) /
                               (math.cos(self.__latitude) * math.sin(zenith)))
                     ) % (2 * math.pi))

        # create the sun for this hour
        return LBSun(datetime, altitude, azimuth, isSolarTime, isDaylightSaving,
                     self.northAngle)

    def calculateSunriseSunset(self, month, day, depression=0.833,
                               isSolarTime=False):
        """Calculate sunrise, noon and sunset.

        Return:
            A dictionary. Keys are ("sunrise", "noon", "sunset")
        """
        datetime = LBDateTime(month, day, hour=12)

        return self.calculateSunriseSunsetFromDateTime(datetime,
                                                       depression,
                                                       isSolarTime)

    # TODO: implement solar time
    def calculateSunriseSunsetFromDateTime(self, datetime, depression=0.833,
                                           isSolarTime=False):
        """Calculate sunrise, sunset and noon for a day of year."""
        solDec, eqOfTime = self.__calculateSolarGeometry(datetime)

        # calculate sunrise and sunset hour
        # if isSolarTime:
        #     noon = .5
        # else:
        noon = (720 -
                4 * math.degrees(self.__longitude) -
                eqOfTime +
                self.timezone * 60
                ) / 1440.0

        sunRiseHourAngle = self.__calculateSunriseHourAngle(solDec, depression)
        sunrise = noon - sunRiseHourAngle * 4 / 1440.0
        sunset = noon + sunRiseHourAngle * 4 / 1440.0

        # convert demical hour to solar hour
        # noon    = self.__calculateSolarTime(24*noon, eqOfTime, isSolarTime)
        # sunrise = self.__calculateSolarTime(24*sunrise, eqOfTime, isSolarTime)
        # sunset  = self.__calculateSolarTime(24*sunset, eqOfTime, isSolarTime)

        # convert to hours
        sunrise *= 24
        sunset *= 24
        noon *= 24

        return {
            "sunrise": LBDateTime(datetime.month, datetime.day,
                                  *self.__calculateHourAndMinute(sunrise)),
            "noon": LBDateTime(datetime.month, datetime.day,
                               *self.__calculateHourAndMinute(noon)),
            "sunset": LBDateTime(datetime.month, datetime.day,
                                 *self.__calculateHourAndMinute(sunset))
        }

    def __calculateSolarGeometry(self, datetime, year=2015):
        """Calculate Solar geometry for an hour of the year.

        Attributes:
            datetime: A Ladybug datetime

        Returns:
            Solar declination: Solar declination in radians
            eqOfTime: Equation of time as minutes
        """
        month, day, hour = datetime.month, datetime.day, datetime.floatHour

        a = 1 if (month < 3) else 0
        y = year + 4800 - a
        m = month + 12 * a - 3

        julianDay = day + math.floor((153 * m + 2) / 5) + 59

        julianDay += (hour - self.timezone) / 24.0 + 365 * y + \
            math.floor(y / 4) - math.floor(y / 100) + \
            math.floor(y / 400) - 32045.5 - 59

        julianCentury = (julianDay - 2451545) / 36525

        # degrees
        geomMeanLongSun = (280.46646 + julianCentury *
                           (36000.76983 + julianCentury * 0.0003032)
                           ) % 360

        # degrees
        geomMeanAnomSun = 357.52911 + julianCentury * \
            (35999.05029 - 0.0001537 * julianCentury)

        eccentOrbit = 0.016708634 - julianCentury * \
            (0.000042037 + 0.0000001267 * julianCentury)

        sunEqOfCtr = math.sin(math.radians(geomMeanAnomSun)) * \
            (1.914602 - julianCentury * (0.004817 + 0.000014 * julianCentury)) + \
            math.sin(math.radians(2 * geomMeanAnomSun)) * \
            (0.019993 - 0.000101 * julianCentury) + \
            math.sin(math.radians(3 * geomMeanAnomSun)) * 0.000289

        # degrees
        sunTrueLong = geomMeanLongSun + sunEqOfCtr

        # AUs
        sunTrueAnom = geomMeanAnomSun + sunEqOfCtr

        # AUs
        sunRadVector = (1.000001018 * (1 - eccentOrbit**2)) / \
            (1 + eccentOrbit * math.cos(math.radians(sunTrueLong)))

        # degrees
        sunAppLong = sunTrueLong - 0.00569 - 0.00478 * \
            math.sin(math.radians(125.04 - 1934.136 * julianCentury))

        # degrees
        meanObliqEcliptic = 23 + \
            (26 + ((21.448 - julianCentury * (46.815 + julianCentury *
                                              (0.00059 - julianCentury *
                                               0.001813)))) / 60) / 60

        # degrees
        obliqueCorr = meanObliqEcliptic + 0.00256 * \
            math.cos(math.radians(125.04 - 1934.136 * julianCentury))

        # degrees
        sunRightAscen = math.degrees(
            math.atan2(math.cos(math.radians(obliqueCorr)) *
                       math.sin(math.radians(sunAppLong)),
                       math.cos(math.radians(sunAppLong))))

        # RADIANS
        solDec = math.asin(math.sin(math.radians(obliqueCorr)) *
                           math.sin(math.radians(sunAppLong)))

        varY = math.tan(math.radians(obliqueCorr / 2)) * \
            math.tan(math.radians(obliqueCorr / 2))

        # minutes
        eqOfTime = 4 \
            * math.degrees(
                varY * math.sin(2 * math.radians(geomMeanLongSun)) -
                2 * eccentOrbit * math.sin(math.radians(geomMeanAnomSun)) +
                4 * eccentOrbit * varY *
                math.sin(math.radians(geomMeanAnomSun)) *
                math.cos(2 * math.radians(geomMeanLongSun)) -
                0.5 * (varY ** 2) *
                math.sin(4 * math.radians(geomMeanLongSun)) -
                1.25 * (eccentOrbit ** 2) *
                math.sin(2 * math.radians(geomMeanAnomSun))
            )

        return solDec, eqOfTime

    def __calculateSunriseHourAngle(self, solarDec, depression=0.833):
        """Calculate hour angle for sunrise time in degrees."""
        hourAngleArg = math.cos(math.radians(90 + depression)) \
            / (math.cos(self.__latitude) * math.cos(solarDec)) \
            - math.tan(self.__latitude) * math.tan(solarDec)

        return math.degrees(math.acos(hourAngleArg))

    def __calculateSolarTime(self, hour, eqOfTime, isSolarTime):
        """Calculate Solar time for an hour."""
        if isSolarTime:
            return hour

        return (
            (hour * 60 + eqOfTime + 4 * math.degrees(self.__longitude) -
             60 * self.timezone) % 1440) / 60

    @staticmethod
    def __calculateHourAndMinute(floatHour):
        """Calculate hour and minutes as integers from a float hour."""
        return int(floatHour), int(round((floatHour - int(floatHour)) * 60))


class LBSun(object):
    """Sun.

    Attributes:
        datetime: A LBDateTime that represents the datetime for this sunVector
        altitude: Solar Altitude in **radians**
        azimuth: Solar Azimuth in **radians**
        isSolarTime: A Boolean that indicates if datetime represents the solar
            time.
        isDaylightSaving: A Boolean that indicates if datetime is calculated
            for Daylight saving period
        northAngle: North angle of the sunpath in Degrees. This will be only
            used to calculate the solar vector.
    """

    __slots__ = ('__datetime', '__altitude', '__azimuth', '__isSolarTime',
                 '__isDaylightSaving', '__northAngle', '__hourlyData', '__data',
                 '__sunVector')
    PI = math.pi

    def __init__(self, datetime, altitude, azimuth, isSolarTime,
                 isDaylightSaving, northAngle, data=None):
        """Init sun."""
        assert hasattr(datetime, 'isLBDateTime'), \
            "datetime must be a LBDateTime (not {})".format(type(datetime))
        self.__datetime = datetime  # read-only

        assert -self.PI <= altitude <= self.PI, \
            "altitude({}) must be between {} and {}." \
            .format(altitude, -self.PI, self.PI)

        self.__altitude = altitude  # read-only

        assert -2 * self.PI <= azimuth <= 2 * self.PI, \
            "azimuth({}) should be between {} and {}." \
            .format(azimuth, -self.PI, self.PI)

        self.__azimuth = azimuth  # read-only
        self.__isSolarTime = isSolarTime
        self.__isDaylightSaving = isDaylightSaving
        # useful to calculate sun vector - sun angle is in degrees
        self.__northAngle = northAngle
        self.data = data  # Place holder for hourly data

        self._calculateSunVector()

    @property
    def datetime(self):
        """Return datetime."""
        return self.__datetime

    @property
    def northAngle(self):
        """Return north angle for +YAxis."""
        return self.__northAngle

    @property
    def HOY(self):
        """Return Hour of the year."""
        return self.__datetime.HOY

    @property
    def altitude(self):
        """Return solar altitude in degrees."""
        return math.degrees(self.__altitude)

    @property
    def azimuth(self):
        """Return solar azimuth in degrees."""
        return math.degrees(self.__azimuth)

    @property
    def altitudeInRadians(self):
        """Return solar altitude in radians."""
        return self.__altitude

    @property
    def azimuthInRadians(self):
        """Return solar azimuth in radians."""
        return self.__azimuth

    @property
    def isSolarTime(self):
        """Return a Boolean that indicates is datetime is solar time."""
        return self.__isSolarTime

    @property
    def isDaylightSaving(self):
        """Return a Boolean that indicates is datetime is solar time."""
        return self.__isDaylightSaving

    @property
    def data(self):
        """Get or set data to this sun position."""
        return self.__data

    @data.setter
    def data(self, d):
        self.__data = d

    @property
    def isDuringDay(self):
        """Check if this sun position is during day."""
        # sun vector is flipped to look to the center
        return self.sunVector.z <= 0

    @property
    def sunVector(self):
        """Sun vector for this sun.

        Sun vector faces downward (e.g. z will be negative.)
        """
        return self.__sunVector

    def _calculateSunVector(self):
        """Calculate sun vector for this sun."""
        zAxis = Vector3(0., 0., -1.)
        xAxis = Vector3(1., 0., 0.)
        northVector = Vector3(0., 1., 0.)

        # rotate north vector based on azimuth, altitude, and north
        _sunvector = northVector \
            .rotate_around(xAxis, self.altitudeInRadians) \
            .rotate_around(zAxis, self.azimuthInRadians) \
            .rotate_around(zAxis, math.radians(-self.northAngle))

        _sunvector.normalize().flip()

        self.__sunVector = _sunvector

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Sun representation."""
        # sun at datetime (X, Y, Z)
        return "Sun at {} (x:{}, y:{}, z:{})".format(
            self.datetime,
            self.sunVector.x,
            self.sunVector.y,
            self.sunVector.z
        )
