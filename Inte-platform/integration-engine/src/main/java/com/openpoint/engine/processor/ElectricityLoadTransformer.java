package com.openpoint.engine.processor;

import com.openpoint.engine.model.ElectricityLoadRequest;
import com.openpoint.engine.model.SAPElectricityLoadRequest;
import org.apache.camel.Exchange;
import org.apache.camel.Processor;
import org.springframework.stereotype.Component;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.xml.XmlMapper;
import java.util.Map;

@Component
public class ElectricityLoadTransformer implements Processor {
    
    private final ObjectMapper jsonMapper = new ObjectMapper();
    private final XmlMapper xmlMapper = new XmlMapper();

    @Override
    public void process(Exchange exchange) throws Exception {
        // Get the body - it might be a Map or String
        Object body = exchange.getIn().getBody();
        
        ElectricityLoadRequest request;
        
        // Check if body is already a Map (parsed by Camel)
        if (body instanceof Map) {
            // Convert Map to ElectricityLoadRequest
            request = jsonMapper.convertValue(body, ElectricityLoadRequest.class);
        } else {
            // Parse JSON string to Java object
            String jsonBody = exchange.getIn().getBody(String.class);
            request = jsonMapper.readValue(jsonBody, ElectricityLoadRequest.class);
        }
        
        // Transform to SAP format
        SAPElectricityLoadRequest sapRequest = new SAPElectricityLoadRequest();
        sapRequest.setRequestID(request.getRequestId());
        sapRequest.setCustomerID(request.getCustomerId());
        sapRequest.setCurrentLoad(request.getCurrentLoadKW());
        sapRequest.setRequestedLoad(request.getRequestedLoadKW());
        sapRequest.setConnectionType(request.getPropertyType());
        
        if (request.getAddress() != null) {
            sapRequest.setCity(request.getAddress().getCity());
            sapRequest.setPinCode(request.getAddress().getPinCode());
        }
        
        // Convert to XML
        String xmlBody = xmlMapper.writeValueAsString(sapRequest);
        
        // Add XML declaration
        xmlBody = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + xmlBody;
        
        // Set the transformed XML as the new body
        exchange.getIn().setBody(xmlBody);
        exchange.getIn().setHeader(Exchange.CONTENT_TYPE, "application/xml");
        
        // Store original request for logging
        exchange.setProperty("transformedXML", xmlBody);
    }
}
