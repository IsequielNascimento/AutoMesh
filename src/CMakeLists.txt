# Header-only dependencies fetched by FetchContent
# nanoflann, Eigen, tinygltf, and happly are available as targets.

# Preprocessor
add_executable(automesh-preproc preproc/main.cpp)
target_link_libraries(automesh-preproc las nanoflann::nanoflann Eigen3::Eigen happly)

# Color Transfer & GLB Exporter
add_executable(automesh-colortransfer colortransfer/main.cpp)
target_link_libraries(automesh-colortransfer nanoflann::nanoflann tinygltf happly)
