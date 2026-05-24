"""
Management command to seed reference data and create a demo tenant/user.

Seeds:
1. Demo tenant and analyst user
2. Emission factors (DEFRA 2024 subset)
3. Airport lookup (major IATA codes)
4. Plant code lookup (demo tenant)
"""
from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from core.models import Tenant
from emissions.models import EmissionFactor
from reference.models import AirportLookup, PlantCodeLookup

User = get_user_model()

EMISSION_FACTORS = [
    # Fuel (Scope 1) - DEFRA 2024
    {'source_db': 'DEFRA_2024', 'category': 'fuel', 'activity_type': 'diesel', 'unit': 'L', 'co2e_per_unit': '2.51210'},
    {'source_db': 'DEFRA_2024', 'category': 'fuel', 'activity_type': 'petrol', 'unit': 'L', 'co2e_per_unit': '2.31440'},
    {'source_db': 'DEFRA_2024', 'category': 'fuel', 'activity_type': 'natural_gas', 'unit': 'kWh', 'co2e_per_unit': '0.18316'},
    {'source_db': 'DEFRA_2024', 'category': 'fuel', 'activity_type': 'lpg', 'unit': 'L', 'co2e_per_unit': '1.53970'},
    {'source_db': 'DEFRA_2024', 'category': 'fuel', 'activity_type': 'heavy_fuel_oil', 'unit': 'L', 'co2e_per_unit': '3.17490'},
    # Electricity (Scope 2) - Various grids
    {'source_db': 'DEFRA_2024', 'category': 'electricity', 'activity_type': 'grid_electricity', 'unit': 'kWh', 'co2e_per_unit': '0.20700', 'region': 'UK'},
    {'source_db': 'EPA_2024', 'category': 'electricity', 'activity_type': 'grid_electricity', 'unit': 'kWh', 'co2e_per_unit': '0.38400', 'region': 'US'},
    {'source_db': 'CEA_2024', 'category': 'electricity', 'activity_type': 'grid_electricity', 'unit': 'kWh', 'co2e_per_unit': '0.71000', 'region': 'IN'},
    {'source_db': 'UBA_2024', 'category': 'electricity', 'activity_type': 'grid_electricity', 'unit': 'kWh', 'co2e_per_unit': '0.38000', 'region': 'DE'},
    # Air travel (Scope 3) - DEFRA 2024 with radiative forcing
    {'source_db': 'DEFRA_2024', 'category': 'travel_air', 'activity_type': 'flight_short_haul_economy', 'unit': 'pkm', 'co2e_per_unit': '0.18287', 'sub_type': 'with_rf'},
    {'source_db': 'DEFRA_2024', 'category': 'travel_air', 'activity_type': 'flight_short_haul_business', 'unit': 'pkm', 'co2e_per_unit': '0.27430', 'sub_type': 'with_rf'},
    {'source_db': 'DEFRA_2024', 'category': 'travel_air', 'activity_type': 'flight_long_haul_economy', 'unit': 'pkm', 'co2e_per_unit': '0.20011', 'sub_type': 'with_rf'},
    {'source_db': 'DEFRA_2024', 'category': 'travel_air', 'activity_type': 'flight_long_haul_premium_economy', 'unit': 'pkm', 'co2e_per_unit': '0.32015', 'sub_type': 'with_rf'},
    {'source_db': 'DEFRA_2024', 'category': 'travel_air', 'activity_type': 'flight_long_haul_business', 'unit': 'pkm', 'co2e_per_unit': '0.58028', 'sub_type': 'with_rf'},
    {'source_db': 'DEFRA_2024', 'category': 'travel_air', 'activity_type': 'flight_long_haul_first', 'unit': 'pkm', 'co2e_per_unit': '0.80040', 'sub_type': 'with_rf'},
    # Hotel (Scope 3) - DEFRA 2024
    {'source_db': 'DEFRA_2024', 'category': 'travel_hotel', 'activity_type': 'hotel_night', 'unit': 'night', 'co2e_per_unit': '21.00000'},
    # Ground transport (Scope 3) - DEFRA 2024
    {'source_db': 'DEFRA_2024', 'category': 'travel_car', 'activity_type': 'car_small_petrol', 'unit': 'km', 'co2e_per_unit': '0.14965'},
    {'source_db': 'DEFRA_2024', 'category': 'travel_car', 'activity_type': 'car_medium_diesel', 'unit': 'km', 'co2e_per_unit': '0.16884'},
    {'source_db': 'DEFRA_2024', 'category': 'travel_car', 'activity_type': 'car_large_diesel', 'unit': 'km', 'co2e_per_unit': '0.20975'},
    {'source_db': 'DEFRA_2024', 'category': 'travel_car', 'activity_type': 'taxi', 'unit': 'km', 'co2e_per_unit': '0.14880'},
]

AIRPORTS = [
    ('DEL', 'Indira Gandhi International', 'New Delhi', 'IN', 28.5562, 77.1000),
    ('BOM', 'Chhatrapati Shivaji Maharaj', 'Mumbai', 'IN', 19.0896, 72.8656),
    ('BLR', 'Kempegowda International', 'Bangalore', 'IN', 13.1986, 77.7066),
    ('MAA', 'Chennai International', 'Chennai', 'IN', 12.9941, 80.1709),
    ('HYD', 'Rajiv Gandhi International', 'Hyderabad', 'IN', 17.2403, 78.4294),
    ('CCU', 'Netaji Subhas Chandra Bose', 'Kolkata', 'IN', 22.6547, 88.4467),
    ('LHR', 'Heathrow', 'London', 'GB', 51.4700, -0.4543),
    ('JFK', 'John F Kennedy International', 'New York', 'US', 40.6413, -73.7781),
    ('SFO', 'San Francisco International', 'San Francisco', 'US', 37.6213, -122.3790),
    ('SIN', 'Changi', 'Singapore', 'SG', 1.3644, 103.9915),
    ('DXB', 'Dubai International', 'Dubai', 'AE', 25.2532, 55.3657),
    ('FRA', 'Frankfurt am Main', 'Frankfurt', 'DE', 50.0379, 8.5622),
    ('CDG', 'Charles de Gaulle', 'Paris', 'FR', 49.0097, 2.5479),
    ('NRT', 'Narita International', 'Tokyo', 'JP', 35.7720, 140.3929),
    ('LAX', 'Los Angeles International', 'Los Angeles', 'US', 33.9425, -118.4081),
    ('ORD', "O'Hare International", 'Chicago', 'US', 41.9742, -87.9073),
    ('AMS', 'Schiphol', 'Amsterdam', 'NL', 52.3105, 4.7683),
    ('HKG', 'Hong Kong International', 'Hong Kong', 'HK', 22.3080, 113.9185),
    ('ICN', 'Incheon International', 'Seoul', 'KR', 37.4602, 126.4407),
    ('SYD', 'Kingsford Smith', 'Sydney', 'AU', -33.9399, 151.1753),
]

PLANT_CODES = [
    ('1000', 'Hamburg Central Plant', 'DE', 'Europe'),
    ('2100', 'Munich Distribution Center', 'DE', 'Europe'),
    ('3000', 'Frankfurt Office Complex', 'DE', 'Europe'),
    ('4000', 'Rotterdam Port Facility', 'NL', 'Europe'),
]


class Command(BaseCommand):
    help = 'Seed reference data: demo tenant, emission factors, airports, plant codes'

    def handle(self, *args, **options):
        self.stdout.write('Seeding reference data...\n')

        # 1. Create demo tenant
        tenant, created = Tenant.objects.get_or_create(
            slug='acme-corp',
            defaults={'name': 'ACME Corporation'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  Created tenant: {tenant.name}'))
        else:
            self.stdout.write(f'  Tenant already exists: {tenant.name}')

        # 2. Create demo user
        if not User.objects.filter(username='analyst').exists():
            user = User.objects.create_user(
                username='analyst',
                email='analyst@acme.example.com',
                password='breathe2024',
                tenant=tenant,
                role='analyst',
            )
            self.stdout.write(self.style.SUCCESS(f'  Created user: {user.username} (password: breathe2024)'))
        else:
            self.stdout.write('  User "analyst" already exists')

        # 3. Seed emission factors
        ef_count = 0
        for ef_data in EMISSION_FACTORS:
            _, created = EmissionFactor.objects.get_or_create(
                activity_type=ef_data['activity_type'],
                source_db=ef_data['source_db'],
                region=ef_data.get('region'),
                defaults={
                    'category': ef_data['category'],
                    'sub_type': ef_data.get('sub_type'),
                    'unit': ef_data['unit'],
                    'co2e_per_unit': Decimal(ef_data['co2e_per_unit']),
                    'valid_from': date(2024, 1, 1),
                }
            )
            if created:
                ef_count += 1
        self.stdout.write(self.style.SUCCESS(f'  Seeded {ef_count} emission factors'))

        # 4. Seed airports
        ap_count = 0
        for iata, name, city, country, lat, lon in AIRPORTS:
            _, created = AirportLookup.objects.get_or_create(
                iata_code=iata,
                defaults={
                    'name': name, 'city': city, 'country': country,
                    'latitude': Decimal(str(lat)), 'longitude': Decimal(str(lon)),
                }
            )
            if created:
                ap_count += 1
        self.stdout.write(self.style.SUCCESS(f'  Seeded {ap_count} airports'))

        # 5. Seed plant codes
        pc_count = 0
        for code, name, country, region in PLANT_CODES:
            _, created = PlantCodeLookup.objects.get_or_create(
                tenant=tenant,
                plant_code=code,
                defaults={
                    'facility_name': name,
                    'country': country,
                    'region': region,
                }
            )
            if created:
                pc_count += 1
        self.stdout.write(self.style.SUCCESS(f'  Seeded {pc_count} plant codes'))

        self.stdout.write(self.style.SUCCESS('\nSeeding complete!'))
        self.stdout.write(f'\n  Login credentials:')
        self.stdout.write(f'    Username: analyst')
        self.stdout.write(f'    Password: breathe2024')
