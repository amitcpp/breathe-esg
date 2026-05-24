# Sources

## Emission Factor Databases

1. **DEFRA 2024** — UK Government GHG Conversion Factors for Company Reporting
   - Publisher: Department for Environment, Food & Rural Affairs (UK)
   - URL: https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024
   - Used for: Fuel combustion (Scope 1), UK grid electricity (Scope 2), air travel, hotel nights, ground transport (Scope 3)
   - Note: Factors include Scope 1 CO₂ + CH₄ + N₂O as CO₂e. Air travel factors include radiative forcing (RF) multiplier.

2. **EPA eGRID 2024** — US Environmental Protection Agency
   - Publisher: US EPA
   - URL: https://www.epa.gov/egrid
   - Used for: US grid electricity emission factors (Scope 2)

3. **CEA 2024** — Central Electricity Authority of India
   - Publisher: Ministry of Power, Government of India
   - URL: https://cea.nic.in/co2-baseline-database/
   - Used for: India grid emission factor (Scope 2)

4. **UBA 2024** — Umweltbundesamt (German Federal Environment Agency)
   - Publisher: UBA
   - URL: https://www.umweltbundesamt.de/themen/co2-emissionen-pro-kilowattstunde-strom
   - Used for: Germany grid emission factor (Scope 2)

## GHG Protocol Standards

5. **GHG Protocol Corporate Standard (Revised Edition)**
   - Publisher: World Resources Institute (WRI) / World Business Council for Sustainable Development (WBCSD)
   - URL: https://ghgprotocol.org/corporate-standard
   - Used for: Scope definitions, organizational boundaries, calculation approaches

6. **GHG Protocol Scope 3 Standard** — Corporate Value Chain (Scope 3) Accounting and Reporting Standard
   - Publisher: WRI / WBCSD
   - URL: https://ghgprotocol.org/standards/scope-3-standard
   - Used for: Category 6 (Business Travel) classification

## Technical References

7. **IATA Airport Codes**
   - Source: OpenFlights Airport Database
   - URL: https://openflights.org/data.html
   - Used for: Airport coordinates for Haversine distance calculation

8. **Haversine Formula**
   - Reference: R.W. Sinnott, "Virtues of the Haversine", Sky and Telescope, vol. 68, no. 2, 1984, p. 159
   - Used for: Great-circle distance calculation for flight emissions

9. **DEFRA Distance Uplift Methodology**
   - Source: DEFRA GHG Conversion Factors Methodology Paper (2024)
   - Used for: 9% distance uplift factor for air travel, haul classification thresholds (3,700 km)

## Technology

10. **Django 4.2 LTS** — https://docs.djangoproject.com/en/4.2/
11. **Django REST Framework 3.14** — https://www.django-rest-framework.org/
12. **React 18** — https://react.dev/
13. **Vite 5** — https://vitejs.dev/
