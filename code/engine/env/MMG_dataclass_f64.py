import taichi as ti
import taichi.math as tm

vec3 = tm.vec3


@ti.dataclass
class Vessel64:
    rho: ti.f64  # Water density
    rho_air: ti.f64  # Air density

    # Vessel particulars
    C_b: ti.f64  # Block Coefficient
    Lpp: ti.f64  # Length over perpendiculars (m)
    B: ti.f64  # Overall width
    d: ti.f64  # Ship draft
    w_P0: ti.f64  # Wake fraction coefficient
    x_G: ti.f64  # X-Coordinate of the center of gravity (m)
    x_P: ti.f64  # X-Coordinate of the propeller (-0.5*Lpp)
    D_p: ti.f64  # Diameter of propeller (m)
    l_R: ti.f64  # Correction of flow straightening factor to yaw-rate
    eta: ti.f64  # Ratio of propeller diameter to rudder span
    kappa: ti.f64  # An experimental constant for expressing "u_R"
    A_R: ti.f64  # Moveable rudder area
    epsilon: ti.f64  # Ratio of wake fraction at propeller and rudder positions
    t_R: ti.f64  # Steering resistance deduction factor
    t_P: ti.f64  # Thrust deduction factor
    x_H_dash: ti.f64  # Longitudinal coordinate of acting point of additional lateral force
    a_H: ti.f64  # Rudder force increase factor

    # Experimental wind projected areas
    A_Fw: ti.f64  # Frontal projected area of the wind
    A_Lw: ti.f64  # Lateral projected area of the wind

    # MMG hydrodynamic derivatives
    R_0_dash: ti.f64  # Frictional resistance coefficient

    # Hull derivatives for longitudinal forces
    X_vv_dash: ti.f64
    X_vr_dash: ti.f64
    X_rr_dash: ti.f64
    X_vvvv_dash: ti.f64

    # Hull derivatives for lateral forces
    Y_v_dash: ti.f64
    Y_r_dash: ti.f64
    Y_vvv_dash: ti.f64
    Y_vvr_dash: ti.f64
    Y_vrr_dash: ti.f64
    Y_rrr_dash: ti.f64

    # Hull derivatives for yaw moment
    N_v_dash: ti.f64
    N_r_dash: ti.f64
    N_vvv_dash: ti.f64
    N_vvr_dash: ti.f64
    N_vrr_dash: ti.f64
    N_rrr_dash: ti.f64

    # Masses and added masses
    displ: ti.f64
    m_x_dash: ti.f64
    m_y_dash: ti.f64

    # Moment of inertia and added moment of inertia
    J_z_dash: ti.f64

    # Wake change coefficients and propeller advance ratio polynomial
    k_0: ti.f64
    k_1: ti.f64
    k_2: ti.f64
    C_1: ti.f64
    C_2_plus: ti.f64
    C_2_minus: ti.f64
    J_slo: ti.f64
    J_int: ti.f64

    # Optional parameters depending on specification
    gamma_R_plus: ti.f64
    gamma_R_minus: ti.f64
    gamma_R: ti.f64
    A_R_Ld_em: ti.f64
    f_alpha: ti.f64
    delta_prop: ti.f64
    m: ti.f64
    m_x: ti.f64
    m_y: ti.f64
    M_inv: tm.mat3
    M_A: tm.mat3


@ti.dataclass
class MinimalVessel:
    m: ti.f64  # Displacement of ship
    C_b: ti.f64  # Block Coefficient
    Lpp: ti.f64  # Length over perpendiculars (m)
    B: ti.f64  # Overall width
    d: ti.f64  # Ship draft
    eta: ti.f64  # Ratio of propeller diameter to rudder span
    A_R: ti.f64  # Rudder Area
    D_p: ti.f64  # Propeller diameter
    f_alpha: ti.f64  # Rudder lift gradient coefficient (optional)
    x_G: ti.f64  # X-Coordinate of the center of gravity (optional)
    w_P0: ti.f64  # Wake fraction coefficient (optional)
    t_P: ti.f64  # Thrust deduction factor (optional)
