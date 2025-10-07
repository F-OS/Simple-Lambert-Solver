from src.lambertlab.solver import load_kernels, compute_c3_tof
from astropy.time import Time

if __name__ == '__main__':
    load_kernels()
    dep='2035-06-25T00:01:09.184'
    arr='2036-01-07T00:01:09.184'
    tof_d, c3, vinf_dep, vinf_arr, branch = compute_c3_tof(dep, arr)
    print('dep,arr,tof_d')
    print(dep, arr, tof_d)
    print('C3:', c3)
    print('vinf_dep (km/s):', vinf_dep)
    print('vinf_arr (km/s):', vinf_arr)
    print('branch:', branch)
