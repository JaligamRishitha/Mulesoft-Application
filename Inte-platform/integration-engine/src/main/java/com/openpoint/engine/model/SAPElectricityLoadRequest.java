package com.openpoint.engine.model;

import com.fasterxml.jackson.dataformat.xml.annotation.JacksonXmlProperty;
import com.fasterxml.jackson.dataformat.xml.annotation.JacksonXmlRootElement;

@JacksonXmlRootElement(localName = "ElectricityLoadRequest")
public class SAPElectricityLoadRequest {
    
    @JacksonXmlProperty(localName = "RequestID")
    private String requestID;
    
    @JacksonXmlProperty(localName = "CustomerID")
    private String customerID;
    
    @JacksonXmlProperty(localName = "CurrentLoad")
    private Integer currentLoad;
    
    @JacksonXmlProperty(localName = "RequestedLoad")
    private Integer requestedLoad;
    
    @JacksonXmlProperty(localName = "ConnectionType")
    private String connectionType;
    
    @JacksonXmlProperty(localName = "City")
    private String city;
    
    @JacksonXmlProperty(localName = "PinCode")
    private String pinCode;

    // Getters and Setters
    public String getRequestID() { return requestID; }
    public void setRequestID(String requestID) { this.requestID = requestID; }
    
    public String getCustomerID() { return customerID; }
    public void setCustomerID(String customerID) { this.customerID = customerID; }
    
    public Integer getCurrentLoad() { return currentLoad; }
    public void setCurrentLoad(Integer currentLoad) { this.currentLoad = currentLoad; }
    
    public Integer getRequestedLoad() { return requestedLoad; }
    public void setRequestedLoad(Integer requestedLoad) { this.requestedLoad = requestedLoad; }
    
    public String getConnectionType() { return connectionType; }
    public void setConnectionType(String connectionType) { this.connectionType = connectionType; }
    
    public String getCity() { return city; }
    public void setCity(String city) { this.city = city; }
    
    public String getPinCode() { return pinCode; }
    public void setPinCode(String pinCode) { this.pinCode = pinCode; }
}
