plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.olrac.signage.tv"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.olrac.signage.tv"
        minSdk = 21
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
        
        buildConfigField("String", "TV_URL", "\"${project.findProperty("TV_URL") ?: "http://10.0.2.2:5174"}\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    kotlinOptions {
        jvmTarget = "1.8"
    }
    buildFeatures {
        buildConfig = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.leanback:leanback:1.0.0")
}
