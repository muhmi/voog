#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <math.h>
#include <numpy/arrayobject.h>

static PyObject *moog_ladder_process(PyObject *self, PyObject *args) {
    PyArrayObject *samples_arr, *cutoff_arr, *state_arr;
    double resonance, sr;

    if (!PyArg_ParseTuple(args, "O!O!dO!d",
                          &PyArray_Type, &samples_arr,
                          &PyArray_Type, &cutoff_arr,
                          &resonance,
                          &PyArray_Type, &state_arr,
                          &sr))
        return NULL;

    npy_intp n = PyArray_SIZE(samples_arr);
    double *samples = (double *)PyArray_DATA(samples_arr);
    double *cutoff_buf = (double *)PyArray_DATA(cutoff_arr);
    double *state = (double *)PyArray_DATA(state_arr);

    npy_intp dims[1] = {n};
    PyArrayObject *out_arr = (PyArrayObject *)PyArray_SimpleNew(1, dims, NPY_DOUBLE);
    if (!out_arr)
        return NULL;
    double *out = (double *)PyArray_DATA(out_arr);

    double s0 = state[0], s1 = state[1], s2 = state[2], s3 = state[3];
    double max_fc = sr * 0.49;

    for (npy_intp i = 0; i < n; i++) {
        double fc = cutoff_buf[i];
        if (fc > max_fc)
            fc = max_fc;

        /* Pre-warp */
        double f = 2.0 * sr * tan(M_PI * fc / sr);
        double g = f / (2.0 * sr);
        double G = g / (1.0 + g);

        /* Feedback */
        double r = resonance * 4.0;
        double S = G * G * G * s0 + G * G * s1 + G * s2 + s3;
        double u = (samples[i] - r * S) / (1.0 + r * G * G * G * G);

        /* Four cascaded one-pole filters */
        double v, lp;
        v = (u - s0) * G;  lp = v + s0;  s0 = lp + v;
        v = (lp - s1) * G; lp = v + s1;  s1 = lp + v;
        v = (lp - s2) * G; lp = v + s2;  s2 = lp + v;
        v = (lp - s3) * G; lp = v + s3;  s3 = lp + v;

        out[i] = lp;
    }

    state[0] = s0; state[1] = s1; state[2] = s2; state[3] = s3;
    return (PyObject *)out_arr;
}

static PyMethodDef module_methods[] = {
    {"moog_ladder_process", moog_ladder_process, METH_VARARGS,
     "Huovilainen Moog ladder filter (24dB/oct), C implementation."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "_moog_filter_c",
    "C extension for Moog ladder filter.",
    -1,
    module_methods
};

PyMODINIT_FUNC PyInit__moog_filter_c(void) {
    import_array();
    return PyModule_Create(&moduledef);
}
