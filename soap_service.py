# soap_service.py

from spyne import Application, rpc, ServiceBase, Integer, Float, Unicode
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

# =====================================================
# SOAP SERVICE
# =====================================================

class TripCalculatorService(ServiceBase):

    @rpc(Float, Float, Integer, _returns=Unicode)
    def calculate_trip_time(ctx, distance, vehicle_range, charging_time_minutes):

        if distance <= 0 or vehicle_range <= 0 or charging_time_minutes <= 0:
            return '{"error": "Les paramètres doivent être positifs"}'

        usable_range = vehicle_range * 0.8
        num_stops = max(0, int(distance / usable_range))
        driving_time_hours = distance / 90.0
        total_charging_hours = (num_stops * charging_time_minutes) / 60.0
        total_time_hours = driving_time_hours + total_charging_hours

        import json
        return json.dumps({
            "distance_km": round(distance, 2),
            "vehicle_range_km": round(vehicle_range, 2),
            "usable_range_km": round(usable_range, 2),
            "num_charging_stops": num_stops,
            "driving_time_hours": round(driving_time_hours, 2),
            "charging_time_hours": round(total_charging_hours, 2),
            "total_time_hours": round(total_time_hours, 2)
        })


# =====================================================
# SOAP APPLICATION (WSGI)
# =====================================================

soap_app = Application(
    [TripCalculatorService],
    tns="ev.trip.calculator",
    in_protocol=Soap11(validator="lxml"),
    out_protocol=Soap11()
)

soap_wsgi_app = WsgiApplication(soap_app)
