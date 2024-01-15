/**
  **************************************************************************
  * @file     at32f403_clock.c
  * @brief    system clock config program
  **************************************************************************
  *                       Copyright notice & Disclaimer
  *
  * The software Board Support Package (BSP) that is made available to
  * download from Artery official website is the copyrighted work of Artery.
  * Artery authorizes customers to use, copy, and distribute the BSP
  * software and its related documentation for the purpose of design and
  * development in conjunction with Artery microcontrollers. Use of the
  * software is governed by this copyright notice and the following disclaimer.
  *
  * THIS SOFTWARE IS PROVIDED ON "AS IS" BASIS WITHOUT WARRANTIES,
  * GUARANTEES OR REPRESENTATIONS OF ANY KIND. ARTERY EXPRESSLY DISCLAIMS,
  * TO THE FULLEST EXTENT PERMITTED BY LAW, ALL EXPRESS, IMPLIED OR
  * STATUTORY OR OTHER WARRANTIES, GUARANTEES OR REPRESENTATIONS,
  * INCLUDING BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
  * FITNESS FOR A PARTICULAR PURPOSE, OR NON-INFRINGEMENT.
  *
  **************************************************************************
  */

/* includes ------------------------------------------------------------------*/
#include "at32f403_clock.h"

/** @addtogroup AT32F403_periph_template
  * @{
  */

/** @addtogroup 403_System_clock_configuration System_clock_configuration
  * @{
  */

/**
  * @brief  delay to wait for stable.
  * @note   this function should be used before reading stable flag.
  * @param  none
  * @retval none
  */
static void wait_stbl(uint32_t delay)
{
  volatile uint32_t i;

  for(i = 0; i < delay; i++);
}

/**
  * @brief  system clock config program
  * @note   the system clock is configured as follow:
  *         system clock (sclk)   = hext / 2 * pll_mult
  *         system clock source   = pll (hext)
  *         - hext                = HEXT_VALUE
  *         - sclk                = 192000000
  *         - ahbdiv              = 1
  *         - ahbclk              = 192000000
  *         - apb2div             = 2
  *         - apb2clk             = 96000000
  *         - apb1div             = 2
  *         - apb1clk             = 96000000
  *         - pll_mult            = 48
  *         - pll_range           = GT72MHZ (greater than 72 mhz)
  * @param  none
  * @retval none
  */
void system_clock_config(void)
{
  /* reset crm */
  crm_reset();

  crm_clock_source_enable(CRM_CLOCK_SOURCE_HEXT, TRUE);

  /* wait for hext stable */
  wait_stbl(HEXT_STABLE_DELAY);

  /* wait till hext is ready */
  while(crm_hext_stable_wait() == ERROR)
  {
  }

  /* config pll clock resource */
  crm_pll_config(CRM_PLL_SOURCE_HEXT_DIV, CRM_PLL_MULT_48, CRM_PLL_OUTPUT_RANGE_GT72MHZ);

  /* enable pll */
  crm_clock_source_enable(CRM_CLOCK_SOURCE_PLL, TRUE);

  /* wait till pll is ready */
  while(crm_flag_get(CRM_PLL_STABLE_FLAG) != SET)
  {
  }

  /* config apb2clk, the maximum frequency of APB1/APB2 clock is 100 MHz  */
  crm_apb2_div_set(CRM_APB2_DIV_2);

  /* config apb1clk, the maximum frequency of APB1/APB2 clock is 100 MHz  */
  crm_apb1_div_set(CRM_APB1_DIV_2);

  /* 1step: config ahbclk div8 */
  crm_ahb_div_set(CRM_AHB_DIV_8);

  /* select pll as system clock source */
  crm_sysclk_switch(CRM_SCLK_PLL);

  /* wait till pll is used as system clock source */
  while(crm_sysclk_switch_status_get() != CRM_SCLK_PLL)
  {
  }

  /* delay */
  wait_stbl(PLL_STABLE_DELAY);

  /* 2step: config ahbclk div2 */
  crm_ahb_div_set(CRM_AHB_DIV_2);

  /* delay */
  wait_stbl(PLL_STABLE_DELAY);

  /* 3step: config ahbclk to target div */
  crm_ahb_div_set(CRM_AHB_DIV_1);

  /* update system_core_clock global variable */
  system_core_clock_update();
}

/**
  * @}
  */

/**
  * @}
  */

