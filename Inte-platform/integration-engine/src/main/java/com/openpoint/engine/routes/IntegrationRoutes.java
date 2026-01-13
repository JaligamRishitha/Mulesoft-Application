package com.openpoint.engine.routes;

import org.apache.camel.builder.RouteBuilder;
import org.springframework.stereotype.Component;

@Component
public class IntegrationRoutes extends RouteBuilder {
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
            .get("/itsm/tickets").to("direct:itsmTickets");

        from("direct:health")
            .setBody(constant("{\"status\":\"healthy\",\"engine\":\"camel-4.2.0\"}"));

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
    }
}
