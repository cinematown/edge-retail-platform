plugins {
    id("io.micronaut.application") version "4.6.2"
}

group = "com.cinematown.edgeretail"
version = "0.1.0"

repositories {
    mavenCentral()
}

dependencies {
    annotationProcessor("io.micronaut:micronaut-inject-java")
    annotationProcessor("io.micronaut.serde:micronaut-serde-processor")
    annotationProcessor("io.micronaut.validation:micronaut-validation-processor")

    implementation("io.micronaut:micronaut-runtime")
    implementation("io.micronaut.data:micronaut-data-jdbc")
    implementation("io.micronaut.mqtt:micronaut-mqttv3")
    implementation("io.micronaut.serde:micronaut-serde-jackson")
    implementation("io.micronaut.sql:micronaut-jdbc-hikari")
    implementation("io.micronaut.validation:micronaut-validation")
    implementation("jakarta.annotation:jakarta.annotation-api")

    runtimeOnly("ch.qos.logback:logback-classic")
    runtimeOnly("com.mysql:mysql-connector-j")
    runtimeOnly("org.yaml:snakeyaml")

    testAnnotationProcessor("io.micronaut:micronaut-inject-java")
    testAnnotationProcessor("io.micronaut.serde:micronaut-serde-processor")
    testAnnotationProcessor("io.micronaut.validation:micronaut-validation-processor")
    testImplementation("io.micronaut:micronaut-inject-java")
    testImplementation("org.junit.jupiter:junit-jupiter-api")
    testRuntimeOnly("org.junit.jupiter:junit-jupiter-engine")
}

application {
    mainClass = "com.cinematown.edgeretail.gateway.Application"
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

micronaut {
    version("4.10.9")
    runtime("netty")
    testRuntime("junit5")
    processing {
        incremental(true)
        annotations("com.cinematown.edgeretail.gateway.*")
    }
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
}
