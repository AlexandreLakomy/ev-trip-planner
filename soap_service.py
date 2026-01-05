#soap_service.py

from spyne import Application, rpc, ServiceBase, Integer, Float, Unicode
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from flask import Flask

app = Flask(__name__)

class TripCalculatorService(ServiceBase):
    """
    Service SOAP pour calculer le temps de trajet en fonction de:
    - La distance à parcourir
    - L'autonomie du véhicule
    - Le temps de chargement
    """
    
    @rpc(Float, Float, Integer, _returns=Unicode)
    def calculate_trip_time(ctx, distance, vehicle_range, charging_time_minutes):
        """
        Calcule le temps total d'un trajet incluant les temps de recharge
        
        Args:
            distance: Distance totale en km
            vehicle_range: Autonomie du véhicule en km
            charging_time_minutes: Temps de recharge en minutes
            
        Returns:
            JSON avec les détails du calcul
        """
        try:
            # Validation des paramètres
            if distance <= 0 or vehicle_range <= 0 or charging_time_minutes <= 0:
                return '{"error": "Les paramètres doivent être positifs"}'
            
            # Autonomie utilisable (80% pour sécurité)
            usable_range = vehicle_range * 0.8
            
            # Nombre d'arrêts de recharge nécessaires
            num_stops = max(0, int(distance / usable_range))
            
            # Temps de conduite (vitesse moyenne 90 km/h)
            driving_time_hours = distance / 90.0
            
            # Temps de recharge total
            total_charging_hours = (num_stops * charging_time_minutes) / 60.0
            
            # Temps total
            total_time_hours = driving_time_hours + total_charging_hours
            
            # Formatage du résultat en JSON
            result = {
                "distance_km": round(distance, 2),
                "vehicle_range_km": round(vehicle_range, 2),
                "usable_range_km": round(usable_range, 2),
                "num_charging_stops": num_stops,
                "driving_time_hours": round(driving_time_hours, 2),
                "charging_time_hours": round(total_charging_hours, 2),
                "total_time_hours": round(total_time_hours, 2),
                "charging_time_per_stop_minutes": charging_time_minutes
            }
            
            import json
            return json.dumps(result)
            
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'
    
    @rpc(Float, Float, _returns=Integer)
    def calculate_charging_stops(ctx, distance, vehicle_range):
        """
        Calcule uniquement le nombre d'arrêts nécessaires
        
        Args:
            distance: Distance totale en km
            vehicle_range: Autonomie du véhicule en km
            
        Returns:
            Nombre d'arrêts de recharge nécessaires
        """
        try:
            usable_range = vehicle_range * 0.8
            return max(0, int(distance / usable_range))
        except:
            return -1

# Configuration de l'application SOAP
soap_app = Application(
    [TripCalculatorService],
    tns='ev.trip.calculator',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

# Créer l'application WSGI
wsgi_app = WsgiApplication(soap_app)

@app.route('/soap', methods=['POST', 'GET'])
def soap_service():
    """Endpoint SOAP accessible via Flask"""
    from flask import request
    
    # Traiter la requête SOAP
    environ = request.environ
    
    def start_response(status, headers):
        pass
    
    response = wsgi_app(environ, start_response)
    
    return b''.join(response)

@app.route('/soap/wsdl')
def soap_wsdl():
    """Fournit le WSDL du service"""
    wsdl = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
             xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
             xmlns:tns="ev.trip.calculator"
             targetNamespace="ev.trip.calculator">
    
    <types>
        <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                    targetNamespace="ev.trip.calculator">
            <xsd:element name="calculate_trip_time">
                <xsd:complexType>
                    <xsd:sequence>
                        <xsd:element name="distance" type="xsd:float"/>
                        <xsd:element name="vehicle_range" type="xsd:float"/>
                        <xsd:element name="charging_time_minutes" type="xsd:integer"/>
                    </xsd:sequence>
                </xsd:complexType>
            </xsd:element>
            <xsd:element name="calculate_trip_timeResponse">
                <xsd:complexType>
                    <xsd:sequence>
                        <xsd:element name="result" type="xsd:string"/>
                    </xsd:sequence>
                </xsd:complexType>
            </xsd:element>
        </xsd:schema>
    </types>
    
    <message name="calculate_trip_timeRequest">
        <part name="parameters" element="tns:calculate_trip_time"/>
    </message>
    <message name="calculate_trip_timeResponse">
        <part name="parameters" element="tns:calculate_trip_timeResponse"/>
    </message>
    
    <portType name="TripCalculatorServicePort">
        <operation name="calculate_trip_time">
            <input message="tns:calculate_trip_timeRequest"/>
            <output message="tns:calculate_trip_timeResponse"/>
        </operation>
    </portType>
    
    <binding name="TripCalculatorServiceBinding" type="tns:TripCalculatorServicePort">
        <soap:binding transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="calculate_trip_time">
            <soap:operation soapAction="calculate_trip_time"/>
            <input>
                <soap:body use="literal"/>
            </input>
            <output>
                <soap:body use="literal"/>
            </output>
        </operation>
    </binding>
    
    <service name="TripCalculatorService">
        <port name="TripCalculatorServicePort" binding="tns:TripCalculatorServiceBinding">
            <soap:address location="http://localhost:5000/soap"/>
        </port>
    </service>
</definitions>"""
    
    from flask import Response
    return Response(wsdl, mimetype='text/xml')

if __name__ == '__main__':
    print("🧼 Service SOAP démarré sur http://localhost:5001/soap")
    print("📄 WSDL disponible sur http://localhost:5001/soap/wsdl")
    app.run(host="0.0.0.0", port=5001, debug=True)
