from datetime import datetime, timedelta
import pytest

from tests import (get_test_context, create_consumption_data)
from custom_components.octopus_energy.sensor_utils import async_calculate_electricity_cost
from custom_components.octopus_energy.api_client import OctopusEnergyApiClient

@pytest.mark.asyncio
async def test_when_electricity_consumption_is_none_then_no_calculation_is_returned():
  # Arrange
  context = get_test_context()

  client = OctopusEnergyApiClient(context["api_key"])
  period_from = datetime.strptime("2022-02-10T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")
  period_to = datetime.strptime("2022-02-11T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")
  latest_date = datetime.strptime("2022-02-09T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")
  tariff_code = "E-1R-SUPER-GREEN-24M-21-07-30-A"

  # Act
  consumption = await async_calculate_electricity_cost(
    client,
    None,
    latest_date,
    period_from,
    period_to,
    tariff_code
  )

  # Assert
  assert consumption == None

@pytest.mark.asyncio
async def test_when_electricity_consumption_is_empty_then_no_calculation_is_returned():
  # Arrange
  context = get_test_context()

  client = OctopusEnergyApiClient(context["api_key"])
  period_from = datetime.strptime("2022-02-10T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")
  period_to = datetime.strptime("2022-02-11T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")
  latest_date = datetime.strptime("2022-02-09T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")
  tariff_code = "E-1R-SUPER-GREEN-24M-21-07-30-A"

  # Act
  consumption = await async_calculate_electricity_cost(
    client,
    [],
    latest_date,
    period_from,
    period_to,
    tariff_code
  )

  # Assert
  assert consumption == None

@pytest.mark.asyncio
async def test_when_electricity_consumption_is_before_latest_date_then_no_calculation_is_returned():
  # Arrange
  context = get_test_context()

  client = OctopusEnergyApiClient(context["api_key"])
  period_from = datetime.strptime("2022-02-10T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")
  period_to = datetime.strptime("2022-02-11T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")
  latest_date = datetime.strptime("2022-02-12T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")
  tariff_code = "E-1R-SUPER-GREEN-24M-21-07-30-A"

  consumption_data = create_consumption_data(period_from, period_to)
  assert consumption_data != None
  assert len(consumption_data) > 0

  # Act
  consumption = await async_calculate_electricity_cost(
    client,
    consumption_data,
    latest_date,
    period_from,
    period_to,
    tariff_code
  )

  # Assert
  assert consumption == None

@pytest.mark.asyncio
@pytest.mark.parametrize("latest_date",[(datetime.strptime("2022-02-09T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")), (None)])
async def test_when_electricity_consumption_available_then_calculation_returned(latest_date):
  # Arrange
  context = get_test_context()

  client = OctopusEnergyApiClient(context["api_key"])
  period_from = datetime.strptime("2022-02-10T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")
  period_to = datetime.strptime("2022-02-11T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")
  tariff_code = "E-1R-SUPER-GREEN-24M-21-07-30-A"
  
  consumption_data = create_consumption_data(period_from, period_to)
  assert consumption_data != None
  assert len(consumption_data) > 0
  assert consumption_data[-1]["interval_end"] == period_to
  assert consumption_data[0]["interval_start"] == period_from

  # Make sure we have rates and standing charges available
  rates = await client.async_get_electricity_rates(tariff_code, period_from, period_to)
  assert rates != None
  assert len(rates) > 0

  standard_charge_result = await client.async_get_electricity_standing_charge(tariff_code, period_from, period_to)
  assert standard_charge_result != None

  # Act
  consumption = await async_calculate_electricity_cost(
    client,
    consumption_data,
    latest_date,
    period_from,
    period_to,
    tariff_code
  )

  # Assert
  assert consumption != None
  assert consumption["standing_charge"] == standard_charge_result["value_inc_vat"]
  assert consumption["total_without_standing_charge"] == 9.63
  assert consumption["total"] == 9.87
  assert consumption["last_calculated_timestamp"] == consumption_data[-1]["interval_end"]

  assert len(consumption["charges"]) == 48

  # Make sure our data is returned in 30 minute increments
  expected_valid_from = period_from
  for item in consumption["charges"]:
      expected_valid_to = expected_valid_from + timedelta(minutes=30)

      assert "from" in item
      assert item["from"] == expected_valid_from
      assert "to" in item
      assert item["to"] == expected_valid_to

      expected_valid_from = expected_valid_to

@pytest.mark.asyncio
async def test_when_electricity_consumption_starting_at_latest_date_then_calculation_returned():
  # Arrange
  context = get_test_context()

  client = OctopusEnergyApiClient(context["api_key"])
  period_from = datetime.strptime("2022-02-10T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")
  period_to = datetime.strptime("2022-02-11T00:00:00Z", "%Y-%m-%dT%H:%M:%S%z")
  tariff_code = "E-1R-SUPER-GREEN-24M-21-07-30-A"
  latest_date = None
  
  consumption_data = create_consumption_data(period_from, period_to, True)
  assert consumption_data != None
  assert len(consumption_data) > 0
  assert consumption_data[0]["interval_end"] == period_to
  assert consumption_data[-1]["interval_start"] == period_from

  # Make sure we have rates and standing charges available
  rates = await client.async_get_electricity_rates(tariff_code, period_from, period_to)
  assert rates != None
  assert len(rates) > 0

  standard_charge_result = await client.async_get_electricity_standing_charge(tariff_code, period_from, period_to)
  assert standard_charge_result != None

  # Act
  consumption_cost = await async_calculate_electricity_cost(
    client,
    consumption_data,
    latest_date,
    period_from,
    period_to,
    tariff_code
  )

  # Assert
  assert consumption_cost != None
  assert consumption_cost["standing_charge"] == standard_charge_result["value_inc_vat"]
  assert consumption_cost["total_without_standing_charge"] == 9.63
  assert consumption_cost["total"] == 9.87
  assert consumption_cost["last_calculated_timestamp"] == consumption_data[0]["interval_end"]

  assert len(consumption_cost["charges"]) == 48

  # Make sure our data is returned in 30 minute increments
  expected_valid_from = period_from
  for item in consumption_cost["charges"]:
      expected_valid_to = expected_valid_from + timedelta(minutes=30)

      assert "from" in item
      assert item["from"] == expected_valid_from
      assert "to" in item
      assert item["to"] == expected_valid_to

      expected_valid_from = expected_valid_to