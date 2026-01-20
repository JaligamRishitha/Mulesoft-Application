package com.openpoint.engine.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public class ElectricityLoadRequest {
    @JsonProperty("requestId")
    private String requestId;
    
    @JsonProperty("customerId")
    private String customerId;
    
    @JsonProperty("serviceType")
    private String serviceType;
    
    @JsonProperty("currentLoadKW")
    private Integer currentLoadKW;
    
    @JsonProperty("requestedLoadKW")
    private Integer requestedLoadKW;
    
    @JsonProperty("propertyType")
    private String propertyType;
    
    @JsonProperty("address")
    private Address address;

    public static class Address {
        @JsonProperty("city")
        private String city;
        
        @JsonProperty("pinCode")
        private String pinCode;

        public String getCity() { return city; }
        public void setCity(String city) { this.city = city; }
        public String getPinCode() { return pinCode; }
        public void setPinCode(String pinCode) { this.pinCode = pinCode; }
    }

    // Getters and Setters
    public String getRequestId() { return requestId; }
    public void setRequestId(String requestId) { this.requestId = requestId; }
    
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    
    public String getServiceType() { return serviceType; }
    public void setServiceType(String serviceType) { this.serviceType = serviceType; }
    
    public Integer getCurrentLoadKW() { return currentLoadKW; }
    public void setCurrentLoadKW(Integer currentLoadKW) { this.currentLoadKW = currentLoadKW; }
    
    public Integer getRequestedLoadKW() { return requestedLoadKW; }
    public void setRequestedLoadKW(Integer requestedLoadKW) { this.requestedLoadKW = requestedLoadKW; }
    
    public String getPropertyType() { return propertyType; }
    public void setPropertyType(String propertyType) { this.propertyType = propertyType; }
    
    public Address getAddress() { return address; }
    public void setAddress(Address address) { this.address = address; }
}
