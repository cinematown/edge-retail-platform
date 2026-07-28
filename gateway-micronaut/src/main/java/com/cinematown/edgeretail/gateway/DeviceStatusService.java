package com.cinematown.edgeretail.gateway;

import jakarta.inject.Singleton;
import jakarta.transaction.Transactional;

@Singleton
public class DeviceStatusService {
    private final GatewayRepository repository;

    DeviceStatusService(GatewayRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public void process(Messages.DeviceStatus status) {
        repository.upsertStatus(status);
    }
}
