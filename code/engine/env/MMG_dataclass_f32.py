import taichi as ti
import taichi.math as tm

vec3 = ti.math.vec3


@ti.dataclass
class _Vessel32Template:
    rho: ti.f32  # Water density
    rho_air: ti.f32  # Air density

    # Vessel particulars
    C_b: ti.f32  # Block Coefficient
    Lpp: ti.f32  # Length over perpendiculars (m)
    B: ti.f32  # Overall width
    d: ti.f32  # Ship draft
    w_P0: ti.f32  # Wake fraction coefficient
    x_G: ti.f32  # X-Coordinate of the center of gravity (m)
    x_P: ti.f32  # X-Coordinate of the propeller (-0.5*Lpp)
    D_p: ti.f32  # Diameter of propeller (m)
    l_R: ti.f32  # Correction of flow straightening factor to yaw-rate
    eta: ti.f32  # Ratio of propeller diameter to rudder span
    kappa: ti.f32  # An experimental constant for expressing "u_R"
    A_R: ti.f32  # Moveable rudder area
    epsilon: ti.f32  # Ratio of wake fraction at propeller and rudder positions
    t_R: ti.f32  # Steering resistance deduction factor
    t_P: ti.f32  # Thrust deduction factor
    x_H_dash: ti.f32  # Longitudinal coordinate of acting point of additional lateral force
    a_H: ti.f32  # Rudder force increase factor

    # Experimental wind projected areas
    A_Fw: ti.f32  # Frontal projected area of the wind
    A_Lw: ti.f32  # Lateral projected area of the wind

    # MMG hydrodynamic derivatives
    R_0_dash: ti.f32  # Frictional resistance coefficient

    # Hull derivatives for longitudinal forces
    X_vv_dash: ti.f32
    X_vr_dash: ti.f32
    X_rr_dash: ti.f32
    X_vvvv_dash: ti.f32

    # Hull derivatives for lateral forces
    Y_v_dash: ti.f32
    Y_r_dash: ti.f32
    Y_vvv_dash: ti.f32
    Y_vvr_dash: ti.f32
    Y_vrr_dash: ti.f32
    Y_rrr_dash: ti.f32

    # Hull derivatives for yaw moment
    N_v_dash: ti.f32
    N_r_dash: ti.f32
    N_vvv_dash: ti.f32
    N_vvr_dash: ti.f32
    N_vrr_dash: ti.f32
    N_rrr_dash: ti.f32

    # Masses and added masses
    displ: ti.f32
    m_x_dash: ti.f32
    m_y_dash: ti.f32

    # Moment of inertia and added moment of inertia
    J_z_dash: ti.f32

    # Wake change coefficients and propeller advance ratio polynomial
    k_0: ti.f32
    k_1: ti.f32
    k_2: ti.f32
    C_1: ti.f32
    C_2_plus: ti.f32
    C_2_minus: ti.f32
    J_slo: ti.f32
    J_int: ti.f32

    # Optional parameters depending on specification
    gamma_R_plus: ti.f32
    gamma_R_minus: ti.f32
    gamma_R: ti.f32
    A_R_Ld_em: ti.f32
    f_alpha: ti.f32
    delta_prop: ti.f32
    m: ti.f32
    m_x: ti.f32
    m_y: ti.f32
    M_inv: tm.mat3
    M_A: tm.mat3


@ti.dataclass
class Vessel32:
    rho: ti.f32  # Water density
    rho_air: ti.f32  # Air density

    # Vessel particulars
    C_b: ti.f32  # Block Coefficient
    Lpp: ti.f32  # Length over perpendiculars (m)
    B: ti.f32  # Overall width
    d: ti.f32  # Ship draft
    w_P0: ti.f32  # Wake fraction coefficient
    x_G: ti.f32  # X-Coordinate of the center of gravity (m)
    x_P: ti.f32  # X-Coordinate of the propeller (-0.5*Lpp)
    D_p: ti.f32  # Diameter of propeller (m)
    l_R: ti.f32  # Correction of flow straightening factor to yaw-rate
    eta: ti.f32  # Ratio of propeller diameter to rudder span
    kappa: ti.f32  # An experimental constant for expressing "u_R"
    A_R: ti.f32  # Moveable rudder area
    epsilon: ti.f32  # Ratio of wake fraction at propeller and rudder positions
    t_R: ti.f32  # Steering resistance deduction factor
    t_P: ti.f32  # Thrust deduction factor
    x_H_dash: ti.f32  # Longitudinal coordinate of acting point of additional lateral force
    a_H: ti.f32  # Rudder force increase factor

    # Experimental wind projected areas
    A_Fw: ti.f32  # Frontal projected area of the wind
    A_Lw: ti.f32  # Lateral projected area of the wind

    # MMG hydrodynamic derivatives
    R_0_dash: ti.f32  # Frictional resistance coefficient

    # Hull derivatives for longitudinal forces
    X_vv_dash: ti.f32
    X_vr_dash: ti.f32
    X_rr_dash: ti.f32
    X_vvvv_dash: ti.f32

    # Hull derivatives for lateral forces
    Y_v_dash: ti.f32
    Y_r_dash: ti.f32
    Y_vvv_dash: ti.f32
    Y_vvr_dash: ti.f32
    Y_vrr_dash: ti.f32
    Y_rrr_dash: ti.f32

    # Hull derivatives for yaw moment
    N_v_dash: ti.f32
    N_r_dash: ti.f32
    N_vvv_dash: ti.f32
    N_vvr_dash: ti.f32
    N_vrr_dash: ti.f32
    N_rrr_dash: ti.f32

    # Masses and added masses
    displ: ti.f32
    m_x_dash: ti.f32
    m_y_dash: ti.f32

    # Moment of inertia and added moment of inertia
    J_z_dash: ti.f32

    # Wake change coefficients and propeller advance ratio polynomial
    k_0: ti.f32
    k_1: ti.f32
    k_2: ti.f32
    C_1: ti.f32
    C_2_plus: ti.f32
    C_2_minus: ti.f32
    J_slo: ti.f32
    J_int: ti.f32

    # Optional parameters depending on specification
    gamma_R_plus: ti.f32
    gamma_R_minus: ti.f32
    gamma_R: ti.f32
    A_R_Ld_em: ti.f32
    f_alpha: ti.f32
    delta_prop: ti.f32
    m: ti.f32
    m_x: ti.f32
    m_y: ti.f32
    M_inv: tm.mat3
    M_A: tm.mat3


@ti.dataclass
class MinimalVessel:
    m: ti.f32  # Displacement of ship
    C_b: ti.f32  # Block Coefficient
    Lpp: ti.f32  # Length over perpendiculars (m)
    B: ti.f32  # Overall width
    d: ti.f32  # Ship draft
    eta: ti.f32  # Ratio of propeller diameter to rudder span
    A_R: ti.f32  # Rudder Area
    D_p: ti.f32  # Propeller diameter
    f_alpha: ti.f32  # Rudder lift gradient coefficient (optional)
    x_G: ti.f32  # X-Coordinate of the center of gravity (optional)
    w_P0: ti.f32  # Wake fraction coefficient (optional)
    t_P: ti.f32  # Thrust deduction factor (optional)
