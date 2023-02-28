import sys

from subscript.co2containment.co2_mass_calculation.co2_mass_calculation import calculate_co2_volume
from subscript.co2containment.co2_mass_calculation.co2_mass_calculation import Co2VolumeData


def main(arguments):
    # Similar to main for co2containment.py
    # Want to use arguments to main to call calculate_co2_volume from co2_mass_calculation,
    # then use this to calculate a summary data frame (volume per date), and
    # export this to a csv file.
    pass


if __name__ == '__main__':
    main(sys.argv[1:])
