#include "Data.h"

double* Data::get_density(const char* file)
{
	double* v;
	std::ifstream f;
	int aux[3];
	f.open(file, std::ios::in | std::ios::binary);
	f.read(reinterpret_cast<char*>(aux), sizeof(int)*3);
	//"i i i",pheno ,nlin,ncol


	f.close();
	return v;
}

Data::Data()
{
	num_partition = 0;
	dim = 0;
	painel = nullptr;
}

Data::~Data()
{
	if (painel != nullptr) {
		for (int i = 0; i < dim; i++) {
			delete[] painel[i];
		}
		delete[] painel;
	}
}

Data::Data(const char* file_space, int num_partition)
{
	//std::sync_with_stdio(false);
	double* values;
	double max, min;
	std::ifstream file;
	int n_lin, n_col;
	int n_mark;
	double** dim_value;
	this->num_partition = num_partition;
	file.open(file_space, std::ios::in);
	file >> n_lin >> n_col >> dim;
	//painel alocation
	painel = new double*[dim];
	for (int i = 0; i < dim; i++) {
		painel[i] = new double[num_partition-1];
	}

	//dimmention alocation
	n_mark = n_col - dim;
	dim_value = new double* [dim];
	for (int i = 0; i < dim; i++) {
		dim_value[i] = new double[n_lin];
	}
	//load cells
	values = new double[n_lin * n_mark];
	for (int l = 0; l < n_lin; l++) {
		if (l % 1000==0) std::cout << l / 1000 << " mil\n";
		for (int c = 0; c < n_mark; c++) {
			file>>values[c * n_lin + l];
		}
		for (int d = 0; d < dim; d++) {
			file >> dim_value[d][l];
		}
	}
	file.close();
	//calculate painel
	for (int d = 0; d < dim; d++) {
		max = -10000;
		min = 10000;
		for (int l = 0; l < n_lin; l++) {
			if (dim_value[d][l] < min) {
				min = dim_value[d][l];
				continue;
			}
			if (dim_value[d][l] > max) {
				max = dim_value[d][l];
			}
		}
		double range = (max - min)/num_partition;
		
		for (int i = 1; i < num_partition; i++) {
			painel[d][i-1] = range * i + min;
		}
	}
	std::cout << "";
	//unalocate
	for (int i = 0; i < dim; i++) {
		delete[] dim_value[i];
	}
	delete[] dim_value;

	delete[] values;

}

void Data::save(const char* file_space)
{
	std::ofstream file;
	file.open(file_space, std::ios::out | std::ios::binary);
	file.write(reinterpret_cast<char*>(&dim), sizeof(int));
	file.write(reinterpret_cast<char*>(&num_partition), sizeof(int));
	for (int d = 0; d < dim; d++) {
		file.write(reinterpret_cast<char*>(painel[d]), sizeof(double)*(num_partition-1));
	}
	file.close();
}

void Data::load(const char* file_space)
{
	std::ifstream file;
	file.open(file_space, std::ios::in | std::ios::binary);
	file.read(reinterpret_cast<char*>(&dim), sizeof(int));
	file.read(reinterpret_cast<char*>(& num_partition), sizeof(int));
	painel = new double* [dim];
	for (int i = 0; i < dim; i++) {
		painel[i] = new double[num_partition - 1];
	}
	for (int d = 0; d < dim; d++) {
		file.read(reinterpret_cast<char*>(painel[d]), sizeof(double) * (num_partition - 1));
	}
	file.close();
}

void Data::apply_cells(const char* file)
{
	double* table = this->get_density(file);

}
