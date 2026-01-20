package com.openpoint.engine.routes;

import com.openpoint.engine.processor.ElectricityLoadTransformer;
import org.apache.camel.builder.RouteBuilder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class IntegrationRoutes extends RouteBuilder {
    
    @Autowired
    private ElectricityLoadTransformer electricityLoadTransformer;
    
    @Override
    public void configure() {
        restConfiguration()
            .component("servlet")
            .bindingMode(org.apache.camel.model.rest.RestBindingMode.json);

        rest("/api")
            .get("/health").to("direct:health")
            .get("/erp/orders").to("direct:erpOrders")
            .get("/erp/inventory").to("direct:erpInventory")
            .get("/crm/customers").to("direct:crmCustomers")
            .get("/crm/leads").to("direct:crmLeads")
            .get("/itsm/tickets").to("direct:itsmTickets")
            .post("/integration/mulesoft/load-request/xml")
                .consumes("application/json")
                .produces("application/xml")
                .to("direct:salesforceToSapIntegration");

        from("direct:health")
            .setBody(constant("{\"status\":\"healthy\",\"engine\":\"camel-4.2.0\",\"features\":[\"json-to-xml\",\"electricity-load-integration\"]}"));

        from("direct:erpOrders")
            .to("http://erp-service:8091/orders?bridgeEndpoint=true")
            .convertBodyTo(String.class);

        from("direct:erpInventory")
            .to("http://erp-service:8091/inventory?bridgeEndpoint=true")
            .convertBodyTo(String.class);

        from("direct:crmCustomers")
            .to("http://crm-service:8092/customers?bridgeEndpoint=true")
            .convertBodyTo(String.class);

        from("direct:crmLeads")
            .to("http://crm-service:8092/leads?bridgeEndpoint=true")
            .convertBodyTo(String.class);

        from("direct:itsmTickets")
            .to("http://itsm-service:8093/tickets?bridgeEndpoint=true")
            .convertBodyTo(String.class);

        // Salesforce to SAP Integration Flow
        from("direct:salesforceToSapIntegration")
            .routeId("salesforce-to-sap-electricity-load")
            .log("Received request from Salesforce: ${body}")
            
            // Store original body
            .setProperty("originalBody", body())
            
            // Log: Received request
            .setBody(constant("{\"integrationId\":1,\"level\":\"INFO\",\"message\":\"Received electricity load request from Salesforce\"}"))
            .setHeader("Content-Type", constant("application/json"))
            .to("http://platform-backend:8080/api/integrations/logs?bridgeEndpoint=true&throwExceptionOnFailure=false")
            
            // Restore original body
            .setBody(exchangeProperty("originalBody"))
            
            // Transform JSON to XML
            .process(electricityLoadTransformer)
            .log("Transformed to XML for SAP: ${body}")
            
            // Store XML body
            .setProperty("xmlBody", body())
            
            // Log: Transformed
            .setBody(constant("{\"integrationId\":1,\"level\":\"INFO\",\"message\":\"Transformed JSON to XML successfully\"}"))
            .setHeader("Content-Type", constant("application/json"))
            .to("http://platform-backend:8080/api/integrations/logs?bridgeEndpoint=true&throwExceptionOnFailure=false")
            
            // Restore XML body
            .setBody(exchangeProperty("xmlBody"))
            
            // Send to SAP ERP Backend on port 8100
            .setHeader("Content-Type", constant("application/xml"))
            .to("http://host.docker.internal:8100/api/integration/mulesoft/load-request/xml?bridgeEndpoint=true&throwExceptionOnFailure=false")
            
            // Store SAP response
            .setProperty("sapResponse", body())
            
            // Log response from SAP
            .log("SAP Response: ${body}")
            .setBody(constant("{\"integrationId\":1,\"level\":\"INFO\",\"message\":\"SAP Order created successfully\"}"))
            .setHeader("Content-Type", constant("application/json"))
            .to("http://platform-backend:8080/api/integrations/logs?bridgeEndpoint=true&throwExceptionOnFailure=false")
            
            // Restore SAP response to return to client
            .setBody(exchangeProperty("sapResponse"))
            .convertBodyTo(String.class);
    }
}
