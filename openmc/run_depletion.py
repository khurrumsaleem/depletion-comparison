from math import pi
import json

import openmc
import openmc.deplete
import numpy as np

###############################################################################
#                              Define materials
###############################################################################

# Instantiate some Materials and register the appropriate Nuclides
uo2 = openmc.Material(material_id=1, name='UO2 fuel at 2.4% wt enrichment')
uo2.set_density('g/cm3', 10.29769)
uo2.add_element('U', 1., enrichment=2.4)
uo2.add_element('O', 2.)

helium = openmc.Material(material_id=2, name='Helium for gap')
helium.set_density('g/cm3', 0.001598)
helium.add_element('He', 2.4044e-4)

zircaloy = openmc.Material(material_id=3, name='Zircaloy 4')
zircaloy.set_density('g/cm3', 6.55)
zircaloy.add_element('Sn', 0.014  , 'wo')
zircaloy.add_element('Fe', 0.00165, 'wo')
zircaloy.add_element('Cr', 0.001  , 'wo')
zircaloy.add_element('Zr', 0.98335, 'wo')

borated_water = openmc.Material(material_id=4, name='Borated water')
borated_water.set_density('g/cm3', 0.740582)
borated_water.add_element('B', 4.0e-5)
borated_water.add_element('H', 5.0e-2)
borated_water.add_element('O', 2.4e-2)
borated_water.add_s_alpha_beta('c_H_in_H2O')

###############################################################################
#                             Create geometry
###############################################################################

# Create surfaces
fuel_or = openmc.ZCylinder(r=0.39218, name='Fuel OR')
clad_ir = openmc.ZCylinder(r=0.40005, name='Clad IR')
clad_or = openmc.ZCylinder(r=0.45720, name='Clad OR')
pitch = 1.25984
box = openmc.model.rectangular_prism(pitch, pitch, boundary_type='reflective')

# Create cells
fuel = openmc.Cell(fill=uo2, region=-fuel_or)
gap = openmc.Cell(fill=helium, region=+fuel_or & -clad_ir)
clad = openmc.Cell(fill=zircaloy, region=+clad_ir & -clad_or)
water = openmc.Cell(fill=borated_water, region=+clad_or & box)

# Create a geometry
geometry = openmc.Geometry([fuel, gap, clad, water])

###############################################################################
#                     Set volumes of depletable materials
###############################################################################

# Since this is a 2D model, use area instead of volume
uo2.volume = pi * fuel_or.r**2

###############################################################################
#                     Transport calculation settings
###############################################################################

# Instantiate a Settings object, set all runtime parameters, and export to XML
settings = openmc.Settings()
settings.batches = 220
settings.inactive = 20
settings.particles = 100000

# Create an initial uniform spatial source distribution over fissionable zones
settings.source = openmc.source.Source(space=openmc.stats.Point())

###############################################################################
#                   Initialize and run depletion calculation
###############################################################################

# Get fission Q values from JSON file generated by get_fission_qvals.py
with open('../data/depletion/serpent_fissq.json', 'r') as f:
    serpent_fission_q = json.load(f)

# Set up depletion operator
chain_file = '../data/depletion/chain_casl_pwr.xml'
op = openmc.deplete.Operator(geometry, settings, chain_file,
    fission_q=serpent_fission_q,
    fission_yield_mode="average")

# cumulative steps in MWd/kg
burnup_cum = np.array([
    0.1, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0,
    12.5, 15.0, 17.5, 20.0, 22.5, 25.0, 27.5, 30.0, 32.5, 35.0, 37.5,
    40.0, 42.5, 45.0, 50.0
])
burnup = np.diff(burnup_cum, prepend=0.0)
power = 174  # W/cm

# Perform simulation using the predictor algorithm
integrator = openmc.deplete.PredictorIntegrator(op, burnup, power, timestep_units='MWd/kg')
integrator.integrate()
