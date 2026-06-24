#include <iostream>
#include <vector>
#include <unordered_map>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <Eigen/Dense>
#include <nanoflann.hpp>
#include "happly.h"

// LASlib includes (installed system-wide in builder phase)
#include <lasreader.hpp>

struct Point {
    double x, y, z;
    unsigned char r, g, b;
    double nx, ny, nz;
    long long grid_key[3];
};

struct PointCloud {
    std::vector<Point> pts;
    inline size_t kdtree_get_point_count() const { return pts.size(); }
    inline double kdtree_get_pt(const size_t idx, const size_t dim) const {
        if (dim == 0) return pts[idx].x;
        else if (dim == 1) return pts[idx].y;
        return pts[idx].z;
    }
    template <class BBOX>
    bool kdtree_get_bbox(BBOX&) const { return false; }
};

int main(int argc, char* argv[]) {
    if (argc < 6) {
        std::cerr << "Usage: " << argv[0] << " <input.laz> <output.ply> <spatial_subsample> <sor_neighbors> <sor_std>\n";
        return 1;
    }

    std::string input_path = argv[1];
    std::string output_path = argv[2];
    double spatial_subsample = std::stod(argv[3]);
    int sor_neighbors = std::stoi(argv[4]);
    double sor_std = std::stod(argv[5]);

    std::cout << "[*] Loading LAZ file: " << input_path << std::endl;
    LASreadOpener lasreadopener;
    lasreadopener.set_file_name(input_path.c_str());
    LASreader* lasreader = lasreadopener.open();
    if (!lasreader) {
        std::cerr << "Error opening file: " << input_path << std::endl;
        return 1;
    }

    std::vector<Point> raw_points;
    while (lasreader->read_point()) {
        Point p;
        p.x = lasreader->point.get_x();
        p.y = lasreader->point.get_y();
        p.z = lasreader->point.get_z();
        if (lasreader->point.have_rgb) {
            p.r = static_cast<unsigned char>(lasreader->point.get_rgb()[0] >> 8);
            p.g = static_cast<unsigned char>(lasreader->point.get_rgb()[1] >> 8);
            p.b = static_cast<unsigned char>(lasreader->point.get_rgb()[2] >> 8);
        } else {
            p.r = 255; p.g = 255; p.b = 255;
        }
        p.nx = p.ny = p.nz = 0.0;
        raw_points.push_back(p);
    }
    lasreader->close();
    delete lasreader;

    std::cout << "[*] Loaded " << raw_points.size() << " points." << std::endl;

    // 1. Voxel Downsampling
    std::cout << "[*] Applying voxel downsampling..." << std::endl;
    std::vector<Point> downsampled_points;
    if (spatial_subsample > 0.0) {
        struct KeyHash {
            std::size_t operator()(const std::array<long long, 3>& key) const {
                return std::hash<long long>()(key[0]) ^ 
                       (std::hash<long long>()(key[1]) << 1) ^ 
                       (std::hash<long long>()(key[2]) << 2);
            }
        };
        std::unordered_map<std::array<long long, 3>, Point, KeyHash> voxel_grid;
        for (const auto& p : raw_points) {
            long long kx = static_cast<long long>(std::floor(p.x / spatial_subsample));
            long long ky = static_cast<long long>(std::floor(p.y / spatial_subsample));
            long long kz = static_cast<long long>(std::floor(p.z / spatial_subsample));
            std::array<long long, 3> key = {kx, ky, kz};
            if (voxel_grid.find(key) == voxel_grid.end()) {
                voxel_grid[key] = p;
            }
        }
        for (const auto& pair : voxel_grid) {
            downsampled_points.push_back(pair.second);
        }
    } else {
        downsampled_points = raw_points;
    }
    std::cout << "[*] Points after downsampling: " << downsampled_points.size() << std::endl;

    // Build initial PointCloud struct for KD-Tree
    PointCloud cloud;
    cloud.pts = downsampled_points;

    using my_kd_tree_t = nanoflann::KDTreeSingleIndexAdaptor<
        nanoflann::L2_Simple_Adaptor<double, PointCloud>,
        PointCloud, 3>;

    my_kd_tree_t index(3, cloud, nanoflann::KDTreeSingleIndexAdaptorParams(10));
    index.buildIndex();

    // 2. SOR Outlier Removal
    std::cout << "[*] Applying SOR filter..." << std::endl;
    std::vector<double> avg_distances(cloud.pts.size());
    double global_mean = 0.0;
    for (size_t i = 0; i < cloud.pts.size(); ++i) {
        double query_pt[3] = { cloud.pts[i].x, cloud.pts[i].y, cloud.pts[i].z };
        std::vector<size_t> ret_index(sor_neighbors);
        std::vector<double> out_dist_sqr(sor_neighbors);
        index.knnSearch(&query_pt[0], sor_neighbors, &ret_index[0], &out_dist_sqr[0]);

        double sum_dist = 0.0;
        for (int j = 1; j < sor_neighbors; ++j) { // skip neighbor 0 (itself)
            sum_dist += std::sqrt(out_dist_sqr[j]);
        }
        avg_distances[i] = sum_dist / (sor_neighbors - 1);
        global_mean += avg_distances[i];
    }
    global_mean /= cloud.pts.size();

    double sq_sum = 0.0;
    for (double d : avg_distances) sq_sum += (d - global_mean) * (d - global_mean);
    double global_std = std::sqrt(sq_sum / cloud.pts.size());

    std::vector<Point> clean_points;
    double sor_threshold = global_mean + sor_std * global_std;
    for (size_t i = 0; i < cloud.pts.size(); ++i) {
        if (avg_distances[i] <= sor_threshold) {
            clean_points.push_back(cloud.pts[i]);
        }
    }
    std::cout << "[*] Points after SOR filter: " << clean_points.size() << std::endl;

    // Rebuild tree on clean points
    cloud.pts = clean_points;
    my_kd_tree_t clean_index(3, cloud, nanoflann::KDTreeSingleIndexAdaptorParams(10));
    clean_index.buildIndex();

    // 3. Normal Estimation
    std::cout << "[*] Estimating normals..." << std::endl;
    const int k_normals = 10;
    for (size_t i = 0; i < cloud.pts.size(); ++i) {
        double query_pt[3] = { cloud.pts[i].x, cloud.pts[i].y, cloud.pts[i].z };
        std::vector<size_t> ret_index(k_normals);
        std::vector<double> out_dist_sqr(k_normals);
        clean_index.knnSearch(&query_pt[0], k_normals, &ret_index[0], &out_dist_sqr[0]);

        // Compute Centroid
        Eigen::Vector3d centroid(0.0, 0.0, 0.0);
        for (int j = 0; j < k_normals; ++j) {
            const auto& p = cloud.pts[ret_index[j]];
            centroid += Eigen::Vector3d(p.x, p.y, p.z);
        }
        centroid /= k_normals;

        // Covariance Matrix
        Eigen::Matrix3d cov = Eigen::Matrix3d::Zero();
        for (int j = 0; j < k_normals; ++j) {
            const auto& p = cloud.pts[ret_index[j]];
            Eigen::Vector3d d = Eigen::Vector3d(p.x, p.y, p.z) - centroid;
            cov += d * d.transpose();
        }

        // Smallest Eigenvector
        Eigen::SelfAdjointEigenSolver<Eigen::Matrix3d> solver(cov);
        Eigen::Vector3d normal = solver.eigenvectors().col(0);
        normal.normalize();

        // Orient towards viewer (assumed looking down -Z or local positive Z)
        if (normal.z() < 0.0) {
            normal = -normal;
        }

        cloud.pts[i].nx = normal.x();
        cloud.pts[i].ny = normal.y();
        cloud.pts[i].nz = normal.z();
    }

    // Write PLY using happly
    std::cout << "[*] Writing PLY to: " << output_path << std::endl;
    happly::PLYData ply_data;
    std::vector<std::array<double, 3>> positions;
    std::vector<std::array<double, 3>> normals;
    std::vector<std::array<unsigned char, 3>> colors;

    for (const auto& p : cloud.pts) {
        positions.push_back({p.x, p.y, p.z});
        normals.push_back({p.nx, p.ny, p.nz});
        colors.push_back({p.r, p.g, p.b});
    }

    ply_data.addVertexPositions(positions);
    ply_data.addVertexNormals(normals);
    ply_data.addVertexColors(colors);
    ply_data.write(output_path, happly::DataFormat::Binary);

    std::cout << "[*] Preprocessing completed successfully." << std::endl;
    return 0;
}
